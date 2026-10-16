"""E2E: everyone's cursor in the editor, HackMD-style.

1. Amy and Ben (guests) open the same new document. Each gets a different
   color, which is also the ring around their avatar in the header.
2. Amy places her cursor: Ben sees her caret in Amy's color, with a name tag
   ("Guest") that fades after a moment and comes back when he hovers the caret.
3. Amy selects text: Ben sees the selection highlighted in Amy's color.
4. Cat opens the document later: she sees Amy's caret at once (not after
   y-protocols' 15 s renewal), and her color differs from both.
5. Amy goes back to My Documents: her caret disappears for Ben and Cat at once
   (not after the 30 s awareness timeout).
"""

import os
import re
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
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "testcases/multi_cursor/output"))
HEADLESS = env_bool("HEADLESS", True)
SLOWMO = int(os.getenv("PW_SLOWMO_MS", "0"))
TIMEOUT_MS = int(os.getenv("PW_TIMEOUT_MS", "30000"))
VISIBLE = re.compile(r"\bis-visible\b")

page_errors: dict[str, list[str]] = {}
# Screenshots are written when the run ends: in dev mode Reflex hot-reloads the
# backend when a new .png appears under testcases/, which would restart the Yjs
# relay in the middle of the test.
shots: dict[str, bytes] = {}


def rgb(hex_color: str, alpha: float | None = None) -> str:
    n = int(hex_color.lstrip("#"), 16)
    r, g, b = n >> 16, (n >> 8) & 255, n & 255
    return f"rgb({r}, {g}, {b})" if alpha is None else f"rgba({r}, {g}, {b}, {alpha})"


def open_doc(context, url: str, doc_id: str, who: str) -> Page:
    page = context.new_page()
    page.set_default_timeout(TIMEOUT_MS)
    page_errors[who] = []
    page.on("pageerror", lambda err: page_errors[who].append(str(err)))
    page.goto(url, wait_until="domcontentloaded")
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
    return page


def my_color(page: Page) -> str:
    return page.evaluate("() => window._codocYjs.provider.awareness.getLocalState().user.color")


def caret_color(page: Page) -> str:
    return page.locator(".yRemoteSelectionHead").evaluate("el => getComputedStyle(el).borderLeftColor")


def awareness(page: Page) -> str:
    return page.evaluate(
        """() => JSON.stringify(Array.from(window._codocYjs.provider.awareness.getStates().entries())
            .map(([id, s]) => [id, s.user, !!s.selection]))"""
    )


def place_cursor(page: Page, line: int, column: int, end_column: int | None = None) -> None:
    """Move the cursor (or select) until our awareness carries it (the binding may lag)."""
    page.wait_for_function(
        """([line, column, endColumn]) => {
            const ed = window.monaco && window.monaco.editor.getEditors()[0];
            const yjs = window._codocYjs;
            if (!ed || !yjs) return false;
            ed.focus();
            ed.setPosition({ lineNumber: 1, column: 1 });  // so the next call is a change
            if (endColumn) ed.setSelection(new window.monaco.Selection(line, column, line, endColumn));
            else ed.setPosition({ lineNumber: line, column });
            const sel = yjs.provider.awareness.getLocalState().selection;
            return !!(sel && sel.head);
        }""",
        arg=[line, column, end_column],
        polling=500,
    )


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    doc_id = f"cursor{uuid.uuid4().hex[:6]}"
    url = f"{BASE_URL}/doc/{doc_id}"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS, slow_mo=SLOWMO)
        contexts = [browser.new_context(viewport={"width": 1280, "height": 760}) for _ in range(3)]
        pages: dict[str, Page] = {}
        try:
            print("Amy and Ben open the document...")
            amy = pages["amy"] = open_doc(contexts[0], url, doc_id, "amy")
            ben = pages["ben"] = open_doc(contexts[1], url, doc_id, "ben")
            amy_color = my_color(amy)
            ben.wait_for_function(
                "(c) => window._codocYjs.provider.awareness.getLocalState().user.color !== c",
                arg=amy_color,
                timeout=10000,
            )
            ben_color = my_color(ben)
            print(f"  colors: Amy {amy_color}, Ben {ben_color}")
            assert amy_color != ben_color, "Amy and Ben got the same color"

            print("Amy places her cursor: Ben sees it in her color, with her name...")
            place_cursor(amy, 1, 9)
            caret = ben.locator(".yRemoteSelectionHead")
            expect(caret).to_have_count(1, timeout=10000)
            assert caret_color(ben) == rgb(amy_color), f"Ben sees Amy's caret in {caret_color(ben)}"
            tag = ben.locator(".codoc-cursor-tag")
            expect(tag).to_have_text("Guest")
            expect(tag).to_have_class(VISIBLE)
            tag_bg = tag.evaluate("el => getComputedStyle(el).backgroundColor")
            assert tag_bg == rgb(amy_color), f"Amy's name tag is {tag_bg}"
            shots["ben_sees_amy.png"] = ben.screenshot(clip={"x": 0, "y": 0, "width": 1280, "height": 260})

            print("  the name tag fades, and hovering the caret brings it back...")
            expect(tag).not_to_have_class(VISIBLE, timeout=6000)
            box = caret.bounding_box()
            assert box, "Amy's caret has no box"
            ben.mouse.move(box["x"] + 1, box["y"] + box["height"] / 2)
            expect(tag).to_have_class(VISIBLE, timeout=5000)
            ben.mouse.move(640, 700)
            expect(tag).not_to_have_class(VISIBLE, timeout=5000)

            print("Amy selects text: Ben sees it highlighted in her color...")
            place_cursor(amy, 1, 3, 17)
            selection = ben.locator(".yRemoteSelection").first
            expect(selection).to_be_visible(timeout=10000)
            sel_bg = selection.evaluate("el => getComputedStyle(el).backgroundColor")
            assert sel_bg == rgb(amy_color, 0.25), f"Amy's selection is {sel_bg}"
            shots["ben_sees_amy_selection.png"] = ben.screenshot(clip={"x": 0, "y": 0, "width": 1280, "height": 260})

            print("Cat opens the document later and sees Amy's caret at once...")
            cat = pages["cat"] = open_doc(contexts[2], url, doc_id, "cat")
            expect(cat.locator(".yRemoteSelectionHead")).to_have_count(1, timeout=5000)
            cat_color = my_color(cat)
            print(f"  Cat's color: {cat_color}")
            assert len({amy_color, ben_color, cat_color}) == 3, "two people share a color"
            assert caret_color(cat) == rgb(amy_color), f"Cat sees Amy's caret in {caret_color(cat)}"

            print("  the header avatars are ringed in the same colors...")
            want = sorted(rgb(c) for c in (amy_color, ben_color, cat_color))
            ben.wait_for_function(
                """(want) => {
                    const rings = Array.from(document.querySelectorAll('header img[alt], img[alt]'))
                        .filter((img) => img.closest('.group'))
                        .map((img) => getComputedStyle(img).borderTopColor).sort();
                    return JSON.stringify(rings) === JSON.stringify(want);
                }""",
                arg=want,
                timeout=10000,
            )

            print("Amy goes back to My Documents: her caret disappears for the others...")
            amy.get_by_role("link", name="My Documents").click()
            amy.wait_for_url(f"{BASE_URL}/")
            expect(ben.locator(".yRemoteSelectionHead")).to_have_count(0, timeout=5000)
            expect(cat.locator(".yRemoteSelectionHead")).to_have_count(0, timeout=5000)
            expect(ben.locator(".codoc-cursor-tag")).to_have_count(0)

            errors = {who: errs for who, errs in page_errors.items() if errs}
            assert not errors, f"page errors: {errors}"
            print("All tests passed!")
            return 0
        except Exception as exc:
            print(f"TEST FAILED: {exc}")
            for who, page in pages.items():
                try:
                    print(f"  {who} awareness: {awareness(page)}")
                except Exception:
                    pass
            for who, page in pages.items():
                try:
                    shots[f"failure_{who}.png"] = page.screenshot(full_page=True)
                except Exception:
                    pass
            raise
        finally:
            for ctx in contexts:
                ctx.close()
            browser.close()
            for name, png in shots.items():
                (OUTPUT_DIR / name).write_bytes(png)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception:
        sys.exit(1)
