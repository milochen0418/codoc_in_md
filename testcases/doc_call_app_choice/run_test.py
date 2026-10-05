"""E2E: the caller chooses the call app; whoever accepts or joins goes straight into it.

Needs two `call.join` providers. The call app (reflex_ddns_livekit_audio_chat)
can stand in for both: `livekit` at localhost and `livekit-alt` at 127.0.0.1 are
two origins of the same server, so a dialog's URL tells which app it opened:

    # call app, e.g. on 3200/8200 (see its README)
    DDNS_INTENT_PROVIDER_CALL_JOIN=livekit,livekit-alt DDNS_INTENT_URL_LIVEKIT=http://localhost:3200 \\
    DDNS_INTENT_URL_LIVEKIT_ALT=http://127.0.0.1:3200 poetry run ./run_test_suite.sh doc_call_app_choice

1. Amy and Ben open the same new document. Amy calls everyone: the chooser
   lists both apps, and Ben is not rung while she chooses. Closing the chooser
   starts no call.
2. Amy calls again and picks the second app. Ben accepts and Dan, who opens the
   document later, joins from the header: neither is asked, both open Amy's
   app, and all three are in the same call.
3. Once everyone hung up, the next call is chosen afresh: Amy picks the first
   app, and Ben follows her there.
"""

import os
import re
import sys
import uuid
from pathlib import Path

from playwright.sync_api import Page, expect, sync_playwright
from reflex_ddns_auth.intent.protocol import app_url


def env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:3000").rstrip("/")
HEADLESS = env_bool("HEADLESS", True)
TIMEOUT_MS = int(os.getenv("PW_TIMEOUT_MS", "30000"))
PROVIDERS = [a.strip() for a in os.getenv("DDNS_INTENT_PROVIDER_CALL_JOIN", "").split(",") if a.strip()]


def open_doc(context, url: str) -> Page:
    page = context.new_page()
    page.set_default_timeout(TIMEOUT_MS)
    page.goto(url, wait_until="domcontentloaded")
    return page


def popup(page: Page):
    return page.get_by_role("alertdialog", name="Incoming call")


def chooser(page: Page):
    return page.get_by_text("Open with", exact=True)


def choose(page: Page, app: str):
    expect(chooser(page)).to_be_visible(timeout=15000)
    page.get_by_role("button").filter(has_text=app_url(app)).click()


def wait_in_call(page: Page, app: str, count: int):
    """In the call, through ``app``, with ``count`` people."""
    frame = page.locator("#ddns-intent-frame")
    expect(frame).to_have_attribute("src", re.compile("^" + re.escape(app_url(app)) + "/intent/call-join\\?"),
                                    timeout=15000)
    expect(chooser(page)).to_have_count(0)
    call = page.frame_locator("#ddns-intent-frame")
    expect(call.locator("#connection-status")).to_have_text("Connected", timeout=60000)
    expect(call.locator(".participant-card")).to_have_count(count, timeout=30000)


def hang_up(page: Page):
    page.frame_locator("#ddns-intent-frame").get_by_role("button", name="Hang up").click()
    expect(page.locator("#ddns-intent-frame")).to_have_count(0, timeout=15000)


def main() -> int:
    output_dir = Path(os.getenv("OUTPUT_DIR", "testcases/doc_call_app_choice/output"))
    output_dir.mkdir(parents=True, exist_ok=True)
    if len(PROVIDERS) < 2:
        print("TEST FAILED: needs two call apps in DDNS_INTENT_PROVIDER_CALL_JOIN (see the docstring)")
        return 1
    first, second = PROVIDERS[:2]
    doc_url = f"{BASE_URL}/doc/choice{uuid.uuid4().hex[:6]}"
    # Saved after the run: a file written in the project during the run makes the
    # dev backend reload, which loses the calls (kept in memory).
    shots: dict[str, bytes] = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=HEADLESS,
            args=["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream",
                  "--autoplay-policy=no-user-gesture-required"],
        )
        contexts = [
            browser.new_context(viewport={"width": 1280, "height": 720}, permissions=["microphone"])
            for _ in range(3)
        ]
        try:
            print("Amy and Ben open the document...")
            amy, ben = (open_doc(ctx, doc_url) for ctx in contexts[:2])
            for page in (amy, ben):
                expect(page.get_by_text("2 active")).to_be_visible(timeout=120000)

            print("Amy calls everyone: the chooser lists both apps, Ben is not rung yet...")
            amy.get_by_role("button", name="Call everyone").click()
            expect(chooser(amy)).to_be_visible(timeout=15000)
            for app in (first, second):
                expect(amy.get_by_role("button").filter(has_text=app_url(app))).to_be_visible()
            shots["chooser"] = amy.screenshot()
            ben.wait_for_timeout(3000)  # the presence loop refreshes calls twice a second
            expect(popup(ben)).to_have_count(0)

            print("Closing the chooser starts no call...")
            amy.locator("[data-intent-dialog]").get_by_role("button", name="Close", exact=True).click()
            expect(chooser(amy)).to_have_count(0, timeout=10000)
            ben.wait_for_timeout(3000)
            for page in (amy, ben):
                expect(page.get_by_role("button", name="Call everyone")).to_be_visible()
                expect(popup(page)).to_have_count(0)

            print(f"Amy calls again and picks {second}...")
            amy.get_by_role("button", name="Call everyone").click()
            choose(amy, second)
            wait_in_call(amy, second, 1)

            print(f"Ben accepts: straight into {second}, not asked...")
            expect(popup(ben)).to_be_visible(timeout=15000)
            popup(ben).get_by_role("button", name="Accept").click()
            wait_in_call(ben, second, 2)
            wait_in_call(amy, second, 2)
            shots["ben_in_call"] = ben.screenshot()

            print(f"Dan opens the document later and joins from the header: {second} too...")
            dan = open_doc(contexts[2], doc_url)
            join = dan.get_by_role("button", name="Join call · 2")
            expect(join).to_be_visible(timeout=120000)
            join.click()
            wait_in_call(dan, second, 3)
            wait_in_call(amy, second, 3)

            print("Everyone hangs up...")
            for page in (dan, ben, amy):
                hang_up(page)
            for page in (amy, ben, dan):
                expect(page.get_by_role("button", name="Call everyone")).to_be_visible(timeout=10000)

            print(f"The next call is chosen afresh: Amy picks {first}, Ben follows...")
            amy.get_by_role("button", name="Call everyone").click()
            choose(amy, first)
            wait_in_call(amy, first, 1)
            expect(popup(ben)).to_be_visible(timeout=15000)
            popup(ben).get_by_role("button", name="Accept").click()
            wait_in_call(ben, first, 2)
            wait_in_call(amy, first, 2)
            hang_up(ben)
            hang_up(amy)
            expect(dan.get_by_role("button", name="Call everyone")).to_be_visible(timeout=10000)

            print("All tests passed!")
            return 0
        except Exception as e:
            print(f"TEST FAILED: {e}")
            for i, ctx in enumerate(contexts):
                for j, pg in enumerate(ctx.pages):
                    shots[f"failure_{i}_{j}"] = pg.screenshot()
            return 1
        finally:
            browser.close()
            for name, png in shots.items():
                (output_dir / f"{name}.png").write_bytes(png)


if __name__ == "__main__":
    sys.exit(main())
