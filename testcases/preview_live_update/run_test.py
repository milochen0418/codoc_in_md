"""E2E: someone reading in Preview Only (or fullscreen) sees the others' edits live.

The others' edits reach a tab through its editor (Yjs -> Monaco ->
update_content -> preview). Preview Only used to take the editor off the page,
so a reader there kept seeing the document as it was when they switched.

1. A writer and a reader open the same new document.
2. The reader switches to Preview Only; the writer types: the reader's preview
   shows it, and the writer sees no cursor of the reader's.
3. The reader reloads, still in Preview Only; the writer types: it shows.
4. The reader goes fullscreen; the writer types: it shows.
5. The reader goes back to Split: both editors hold each typed line once.
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
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "testcases/preview_live_update/output"))
HEADLESS = env_bool("HEADLESS", True)
SLOWMO = int(os.getenv("PW_SLOWMO_MS", "0"))
TIMEOUT_MS = int(os.getenv("PW_TIMEOUT_MS", "30000"))
# The writer's line reaches the reader's preview in well under a second.
LIVE_MS = 8000
ACTIVE = re.compile(r"\bbg-violet-100\b")

page_errors: dict[str, list[str]] = {}
# Written when the run ends: a new .png under testcases/ hot-reloads a dev backend.
shots: dict[str, bytes] = {}


def wait_bound(page: Page, doc_id: str) -> None:
    """In the document's Yjs room, with the editor holding the room's text."""
    page.wait_for_function(
        """(docId) => {
            const yjs = window._codocYjs;
            const ed = window.monaco && window.monaco.editor.getEditors()[0];
            const model = ed && ed.getModel();
            return !!(yjs && yjs.docId === docId && model && yjs.ytext.length > 0
                && yjs.ytext.toString() === model.getValue());
        }""",
        arg=doc_id,
        timeout=60000,
    )


def watch_errors(page: Page, who: str) -> None:
    """Collect the page's uncaught errors.

    Skipped: errors thrown by Reflex's own window.onerror, which reads error.name
    and so throws for a browser error event without an error object, such as
    Monaco stopping its worker while the worker's script still loads (a view
    switch soon after the page opened). An exception of the page itself is
    reported on its own.
    """
    page_errors[who] = []

    def on_error(err) -> None:
        if "at window.onerror" not in (err.stack or ""):
            page_errors[who].append(str(err))

    page.on("pageerror", on_error)


def open_doc(context, url: str, doc_id: str, who: str) -> Page:
    page = context.new_page()
    page.set_default_timeout(TIMEOUT_MS)
    watch_errors(page, who)
    page.goto(url, wait_until="domcontentloaded")
    page.locator("#editor-pane .monaco-editor").wait_for(state="visible", timeout=60000)
    wait_bound(page, doc_id)
    return page


def type_line(page: Page, text: str) -> None:
    """Type a new paragraph at the end of the document, as a person would."""
    page.evaluate(
        """() => {
            const ed = window.monaco.editor.getEditors()[0];
            const model = ed.getModel();
            const last = model.getLineCount();
            ed.focus();
            ed.setPosition({ lineNumber: last, column: model.getLineMaxColumn(last) });
        }"""
    )
    page.keyboard.type(f"\n\n{text}")


def editor_text(page: Page) -> str:
    return page.evaluate("() => window.monaco.editor.getEditors()[0].getModel().getValue()")


def view(page: Page, title: str) -> None:
    button = page.locator(f'button[title="{title}"]')
    button.click()
    expect(button).to_have_class(ACTIVE)


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    suffix = uuid.uuid4().hex[:6]
    doc_id = f"preview{suffix}"
    url = f"{BASE_URL}/doc/{doc_id}"
    lines = [f"LiveOne{suffix}", f"LiveTwo{suffix}", f"LiveThree{suffix}"]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS, slow_mo=SLOWMO)
        contexts = [browser.new_context(viewport={"width": 1280, "height": 760}) for _ in range(2)]
        pages: dict[str, Page] = {}
        try:
            print(f"Document: {url}")
            print("The writer and the reader open the document...")
            writer = pages["writer"] = open_doc(contexts[0], url, doc_id, "writer")
            reader = pages["reader"] = open_doc(contexts[1], url, doc_id, "reader")
            preview = reader.locator("#preview-pane")

            print("The reader switches to Preview Only; the writer types...")
            view(reader, "Preview Only")
            expect(reader.locator("#editor-pane")).to_be_hidden()
            type_line(writer, lines[0])
            expect(preview, "Preview Only shows the writer's line").to_contain_text(lines[0], timeout=LIVE_MS)
            expect(writer.locator(".yRemoteSelectionHead"), "the reader parks no cursor").to_have_count(0)
            shots["reader_preview.png"] = reader.screenshot()

            print("The reader reloads, still in Preview Only; the writer types...")
            reader.reload(wait_until="domcontentloaded")
            expect(reader.locator('button[title="Preview Only"]')).to_have_class(ACTIVE, timeout=60000)
            expect(preview).to_contain_text(lines[0], timeout=60000)
            type_line(writer, lines[1])
            expect(preview, "Preview Only after a reload shows the writer's line").to_contain_text(
                lines[1], timeout=LIVE_MS
            )
            shots["reader_preview_after_reload.png"] = reader.screenshot()

            print("The reader goes fullscreen; the writer types...")
            reader.locator('button[title^="Fullscreen Preview"]').click()
            expect(reader.locator("html")).to_have_class(re.compile(r"\bcodoc-fullscreen\b"))
            expect(reader.locator("#editor-pane")).to_be_hidden()
            type_line(writer, lines[2])
            expect(preview, "fullscreen shows the writer's line").to_contain_text(lines[2], timeout=LIVE_MS)
            shots["reader_fullscreen.png"] = reader.screenshot()
            reader.keyboard.press("Escape")
            expect(reader.locator("html")).not_to_have_class(re.compile(r"\bcodoc-fullscreen\b"))

            print("The reader goes back to Split: both editors hold each line once...")
            view(reader, "Split View")
            reader.locator("#editor-pane .monaco-editor").wait_for(state="visible")
            wait_bound(reader, doc_id)
            for who, page in pages.items():
                text = editor_text(page)
                for line in lines:
                    assert text.count(line) == 1, f"{who}'s editor has {line!r} {text.count(line)} times:\n{text}"
            assert editor_text(reader) == editor_text(writer), "the two editors differ"

            errors = {who: errs for who, errs in page_errors.items() if errs}
            assert not errors, f"page errors: {errors}"
            print("All tests passed!")
            return 0
        except Exception as exc:
            print(f"TEST FAILED: {exc}")
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
