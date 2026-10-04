"""E2E: call everyone on a document, through the `call.join` DDNS Intent.

Needs the call app (reflex_ddns_livekit_audio_chat) running too, named as the
`call.join` provider (there is no re-ddns registry locally):

    # call app, e.g. on 3200/8200 (see its README)
    DDNS_INTENT_PROVIDER_CALL_JOIN=livekit DDNS_INTENT_URL_LIVEKIT=http://localhost:3200 \\
    poetry run ./run_test_suite.sh doc_call

1. Three guests (Amy, Ben, Cat) open the same new document: 3 active.
2. Amy calls everyone: her dialog joins the call app, titled with the document;
   Ben and Cat get an incoming call. The call id is not in the iframe URL.
3. Cat declines: no popup, the header offers "Join call · 1". Ben accepts:
   Amy and Ben hear each other.
4. Dan opens the document later: the header shows "Join call · 2" and he joins.
5. Ben minimizes the call: it keeps running in the tray (audio still flows).
6. Ben closes it from the tray, Dan and Amy hang up: the call is over and
   everyone is offered "Call everyone" again.
"""

import os
import sys
import uuid
from pathlib import Path

from playwright.sync_api import Page, expect, sync_playwright


def env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:3000").rstrip("/")
HEADLESS = env_bool("HEADLESS", True)
TIMEOUT_MS = int(os.getenv("PW_TIMEOUT_MS", "30000"))
TITLE = "Start typing your masterpiece..."  # the heading of a new document

_INBOUND_AUDIO_BYTES = """async () => {
    const room = window.livekitClient && window.livekitClient.room;
    if (!room) return -1;
    let total = 0;
    for (const p of room.remoteParticipants.values()) {
        for (const pub of p.audioTrackPublications.values()) {
            const track = pub.track;
            if (!track || !track.receiver) continue;
            const stats = await track.receiver.getStats();
            stats.forEach((r) => { if (r.type === 'inbound-rtp') total += r.bytesReceived || 0; });
        }
    }
    return total;
}"""


def open_doc(context, url: str) -> Page:
    page = context.new_page()
    page.set_default_timeout(TIMEOUT_MS)
    page.goto(url, wait_until="domcontentloaded")
    return page


def popup(page: Page):
    return page.get_by_role("alertdialog", name="Incoming call")


def call_frame(page: Page):
    """The call dialog in front."""
    return page.frame_locator("#ddns-intent-frame")


def call_page(page: Page):
    """The call app's page, in front or minimized."""
    return page.query_selector('iframe[data-intent-action="call.join"]').content_frame()


def wait_in_call(page: Page, count: int):
    frame = call_frame(page)
    expect(frame.locator("#connection-status")).to_have_text("Connected", timeout=60000)
    expect(frame.locator(".participant-card")).to_have_count(count, timeout=30000)


def assert_audio_flows(*pages: Page):
    for page in pages:
        first = call_page(page).evaluate(_INBOUND_AUDIO_BYTES)
        for _ in range(30):  # a just-joined call may take a moment to deliver its first bytes
            if first > 0:
                break
            page.wait_for_timeout(500)
            first = call_page(page).evaluate(_INBOUND_AUDIO_BYTES)
        page.wait_for_timeout(3000)
        second = call_page(page).evaluate(_INBOUND_AUDIO_BYTES)
        print(f"  inbound audio bytes: {first} -> {second}")
        assert second > first > 0, "no audio received in the call"


def main() -> int:
    output_dir = Path(os.getenv("OUTPUT_DIR", "testcases/doc_call/output"))
    output_dir.mkdir(parents=True, exist_ok=True)
    doc_url = f"{BASE_URL}/doc/call{uuid.uuid4().hex[:6]}"

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=HEADLESS,
            args=["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream",
                  "--autoplay-policy=no-user-gesture-required"],
        )
        contexts = [
            browser.new_context(viewport={"width": 1280, "height": 720}, permissions=["microphone"])
            for _ in range(4)
        ]
        try:
            print("Amy, Ben and Cat open the document...")
            amy, ben, cat = (open_doc(ctx, doc_url) for ctx in contexts[:3])
            for page in (amy, ben, cat):
                expect(page.get_by_text("3 active")).to_be_visible(timeout=120000)

            print("Amy calls everyone...")
            amy.get_by_role("button", name="Call everyone").click()
            wait_in_call(amy, 1)
            expect(call_frame(amy).get_by_role("heading", name=TITLE)).to_be_visible()
            src = amy.locator("#ddns-intent-frame").get_attribute("src")
            assert "_intent_wait=1" in src and "room=" not in src, f"call id in the URL: {src}"
            for page in (ben, cat):
                expect(popup(page)).to_be_visible(timeout=15000)
                expect(popup(page)).to_contain_text("is calling")
            expect(popup(amy)).to_have_count(0)
            ben.screenshot(path=str(output_dir / "incoming_call.png"))

            print("Cat declines; Ben accepts and both hear each other...")
            popup(cat).get_by_role("button", name="Decline").click()
            expect(popup(cat)).to_have_count(0, timeout=10000)
            expect(cat.get_by_role("button", name="Join call · 1")).to_be_visible(timeout=10000)
            popup(ben).get_by_role("button", name="Accept").click()
            expect(popup(ben)).to_have_count(0, timeout=10000)
            wait_in_call(ben, 2)
            wait_in_call(amy, 2)
            assert_audio_flows(amy, ben)
            amy.screenshot(path=str(output_dir / "in_call.png"))
            cat.wait_for_timeout(2000)  # declined once: not rung again
            expect(popup(cat)).to_have_count(0)

            print("Dan opens the document later and joins the call in progress...")
            dan = open_doc(contexts[3], doc_url)
            join = dan.get_by_role("button", name="Join call · 2")
            expect(join).to_be_visible(timeout=120000)
            join.click()
            wait_in_call(dan, 3)
            wait_in_call(amy, 3)
            expect(cat.get_by_role("button", name="Join call · 3")).to_be_visible(timeout=10000)

            print("Ben minimizes the call: it keeps running in the tray...")
            ben.get_by_role("button", name="Minimize").click()
            tray = ben.get_by_role("button", name=f"Show Call · {TITLE}")
            expect(tray).to_be_visible(timeout=10000)
            ben.wait_for_timeout(4000)
            expect(call_frame(amy).locator(".participant-card")).to_have_count(3)
            assert_audio_flows(ben)
            ben.screenshot(path=str(output_dir / "call_in_tray.png"))

            print("Everyone leaves: the call is over...")
            ben.get_by_role("button", name=f"Close Call · {TITLE}").click()
            expect(tray).to_have_count(0, timeout=10000)
            wait_in_call(amy, 2)
            expect(cat.get_by_role("button", name="Join call · 2")).to_be_visible(timeout=10000)
            call_frame(dan).get_by_role("button", name="Hang up").click()
            expect(dan.locator("#ddns-intent-frame")).to_have_count(0, timeout=15000)
            wait_in_call(amy, 1)
            call_frame(amy).get_by_role("button", name="Hang up").click()
            expect(amy.locator("#ddns-intent-frame")).to_have_count(0, timeout=15000)
            for page in (amy, ben, cat, dan):
                expect(page.get_by_role("button", name="Call everyone")).to_be_visible(timeout=10000)

            print("All tests passed!")
            return 0
        except Exception as e:
            print(f"TEST FAILED: {e}")
            for i, ctx in enumerate(contexts):
                for j, pg in enumerate(ctx.pages):
                    pg.screenshot(path=str(output_dir / f"failure_{i}_{j}.png"))
            return 1
        finally:
            browser.close()


if __name__ == "__main__":
    sys.exit(main())
