"""E2E: the header shows who is really on the document.

1. Amy and Ben (guests) open the same new document: each sees two avatars.
2. Amy places her cursor, so Ben sees her caret.
3. Amy's browser goes away without any goodbye (her context is closed, so no
   beforeunload/pagehide runs): within a few seconds Ben sees one avatar and no
   caret. The backend notices her Reflex socket is gone, and the Yjs relay tells
   the room that her awareness client left.
4. Cat opens the document and reloads it: she keeps her color, and Ben keeps
   seeing two avatars.
5. Cat goes back to My Documents: Ben sees one avatar.
"""

import os
import sys
import time
import uuid
from pathlib import Path

from playwright.sync_api import Page, expect, sync_playwright


def env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:3000").rstrip("/")
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "testcases/presence_leave/output"))
HEADLESS = env_bool("HEADLESS", True)
SLOWMO = int(os.getenv("PW_SLOWMO_MS", "0"))
TIMEOUT_MS = int(os.getenv("PW_TIMEOUT_MS", "30000"))
# A closed tab must leave the header (and its caret the editor) well within the
# 30 s y-protocols awareness timeout and the 10 s presence TTL.
LEAVE_WITHIN_S = 12

page_errors: dict[str, list[str]] = {}
# Screenshots are written when the run ends: in dev mode Reflex hot-reloads the
# backend when a new .png appears under testcases/, which would restart the Yjs
# relay in the middle of the test.
shots: dict[str, bytes] = {}

AVATARS_JS = "Array.from(document.querySelectorAll('img[alt]')).filter((img) => img.closest('.group')).length"


def wait_ready(page: Page, doc_id: str) -> None:
    page.locator("#editor-pane .monaco-editor").wait_for(state="visible", timeout=60000)
    # Connected to the document's Yjs room, with our name and color published.
    page.wait_for_function(
        """(docId) => {
            const yjs = window._codocYjs;
            const me = yjs && yjs.docId === docId && yjs.provider.awareness.getLocalState();
            return !!(me && me.user && me.user.name && me.user.color);
        }""",
        arg=doc_id,
        timeout=60000,
    )


def open_doc(context, url: str, doc_id: str, who: str) -> Page:
    page = context.new_page()
    page.set_default_timeout(TIMEOUT_MS)
    page_errors[who] = []
    page.on("pageerror", lambda err: page_errors[who].append(str(err)))
    page.goto(url, wait_until="domcontentloaded")
    wait_ready(page, doc_id)
    return page


def my_color(page: Page) -> str:
    return page.evaluate("() => window._codocYjs.provider.awareness.getLocalState().user.color")


def avatars(page: Page) -> int:
    return page.evaluate(f"() => {AVATARS_JS}")


def wait_avatars(page: Page, count: int, timeout_ms: int) -> float:
    """Wait until the header shows ``count`` avatars; returns how long it took."""
    t0 = time.monotonic()
    page.wait_for_function(f"(n) => {AVATARS_JS} === n", arg=count, timeout=timeout_ms, polling=250)
    return time.monotonic() - t0


def place_cursor(page: Page, line: int, column: int) -> None:
    """Move the cursor until our awareness carries it (the binding may lag)."""
    page.wait_for_function(
        """([line, column]) => {
            const ed = window.monaco && window.monaco.editor.getEditors()[0];
            const yjs = window._codocYjs;
            if (!ed || !yjs) return false;
            ed.focus();
            ed.setPosition({ lineNumber: 1, column: 1 });  // so the next call is a change
            ed.setPosition({ lineNumber: line, column });
            const sel = yjs.provider.awareness.getLocalState().selection;
            return !!(sel && sel.head);
        }""",
        arg=[line, column],
        polling=500,
    )


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    doc_id = f"leave{uuid.uuid4().hex[:6]}"
    url = f"{BASE_URL}/doc/{doc_id}"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS, slow_mo=SLOWMO)
        contexts = [browser.new_context(viewport={"width": 1280, "height": 760}) for _ in range(3)]
        pages: dict[str, Page] = {}
        try:
            print("Amy and Ben open the document: both see two avatars...")
            amy = pages["amy"] = open_doc(contexts[0], url, doc_id, "amy")
            ben = pages["ben"] = open_doc(contexts[1], url, doc_id, "ben")
            wait_avatars(amy, 2, 15000)
            wait_avatars(ben, 2, 15000)

            print("Amy places her cursor: Ben sees her caret...")
            place_cursor(amy, 1, 5)
            expect(ben.locator(".yRemoteSelectionHead")).to_have_count(1, timeout=10000)
            shots["ben_with_amy.png"] = ben.screenshot(clip={"x": 0, "y": 0, "width": 1280, "height": 260})

            print("Amy's browser goes away without a goodbye...")
            pages.pop("amy")
            contexts[0].close()
            took = wait_avatars(ben, 1, LEAVE_WITHIN_S * 1000)
            print(f"  her avatar left Ben's header after {took:.1f} s")
            expect(ben.locator(".yRemoteSelectionHead")).to_have_count(0, timeout=LEAVE_WITHIN_S * 1000)
            expect(ben.locator(".codoc-cursor-tag")).to_have_count(0)
            print("  and her caret is gone")
            shots["ben_after_amy_left.png"] = ben.screenshot(clip={"x": 0, "y": 0, "width": 1280, "height": 260})

            print("Cat opens the document and reloads it: same color, still two avatars...")
            cat = pages["cat"] = open_doc(contexts[2], url, doc_id, "cat")
            wait_avatars(ben, 2, 15000)
            cat_color = my_color(cat)
            cat.reload(wait_until="domcontentloaded")
            wait_ready(cat, doc_id)
            # The header settles once her presence is reported again.
            wait_avatars(cat, 2, 15000)
            wait_avatars(ben, 2, 15000)
            time.sleep(PRESENCE_SETTLE_S)
            assert avatars(ben) == 2, f"Ben sees {avatars(ben)} avatars after Cat's reload"
            assert my_color(cat) == cat_color, f"Cat's color changed on reload: {cat_color} -> {my_color(cat)}"
            print(f"  Cat kept {cat_color}")

            print("Cat goes back to My Documents: Ben sees one avatar...")
            cat.get_by_role("link", name="My Documents").click()
            cat.wait_for_url(f"{BASE_URL}/")
            took = wait_avatars(ben, 1, LEAVE_WITHIN_S * 1000)
            print(f"  her avatar left after {took:.1f} s")
            # Through leave_document (page unmount), not the presence TTL.
            assert took < 6, f"leaving the page took {took:.1f} s to show (the 10 s TTL path?)"

            errors = {who: errs for who, errs in page_errors.items() if errs}
            assert not errors, f"page errors: {errors}"
            print("All tests passed!")
            return 0
        except Exception as exc:
            print(f"TEST FAILED: {exc}")
            for who, page in pages.items():
                try:
                    shots[f"fail_{who}.png"] = page.screenshot()
                except Exception:
                    pass
            return 1
        finally:
            for name, data in shots.items():
                (OUTPUT_DIR / name).write_bytes(data)
            browser.close()


# After a reload the old presence loop may linger for a few seconds; give the
# header time to show it settled on the same people.
PRESENCE_SETTLE_S = 6

if __name__ == "__main__":
    sys.exit(main())
