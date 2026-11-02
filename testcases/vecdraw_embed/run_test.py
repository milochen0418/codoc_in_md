"""E2E: drawings from Codoc in VecDraw in the preview.

A stand-in for the app serves the page here, so the suite needs no other app, and counts how often
each drawing is loaded. Run it with

    VECDRAW_BACKEND_URL=http://127.0.0.1:8399 poetry run ./run_test_suite.sh vecdraw_embed

1. {%vecdraw <id> %} and {%vecdraw <its link> %} show one frame each, over their boxes.
2. The frame says how wide its drawing is compared to its height: the box follows, also when the
   pane changes width. A tall drawing stops at 70% of the window.
3. Edits above a frame move it with its box and don't reload it.
4. A line that isn't a drawing stays text.
5. A printed page has the picture and no frames.
"""

import os
import sys
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import Page, sync_playwright


def env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:3000").rstrip("/")
VECDRAW_URL = os.getenv("VECDRAW_BACKEND_URL", "").rstrip("/")
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "testcases/vecdraw_embed/output"))
HEADLESS = env_bool("HEADLESS", True)
TIMEOUT_MS = int(os.getenv("PW_TIMEOUT_MS", "30000"))

RATIOS = {"wide": 0.5, "tall": 3}
PAGE = """<!doctype html><html><body style="margin:0;background:#def">
<script>parent.postMessage({type: "vecdraw-embed", ratio: %s}, "*");</script></body></html>"""
# A 1x1 PNG.
PICTURE = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010806000000" "1f15c4890000000a49444154789c6300010000050001"
    "0d0a2db40000000049454e44ae426082"
)

loads: dict[str, int] = {}
pictures: dict[str, int] = {}


class Stand(BaseHTTPRequestHandler):
    def do_GET(self):
        parts = urlparse(self.path).path.strip("/").split("/")
        if parts[:2] == ["_vecdraw", "embed"] and len(parts) == 3:
            loads[parts[2]] = loads.get(parts[2], 0) + 1
            self.answer((PAGE % RATIOS.get(parts[2], 1)).encode("utf-8"), "text/html; charset=utf-8")
        elif parts[:2] == ["_vecdraw", "og"] and parts[-1] == "image.png":
            pictures[parts[2]] = pictures.get(parts[2], 0) + 1
            self.answer(PICTURE, "image/png")
        else:
            self.send_error(404)

    def answer(self, body: bytes, kind: str) -> None:
        self.send_response(200)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def wait_bound(page: Page, doc_id: str) -> None:
    page.wait_for_function(
        """(docId) => {
            const yjs = window._codocYjs;
            const ed = window.monaco && window.monaco.editor.getEditors()[0];
            const model = ed && ed.getModel();
            return !!(yjs && yjs.docId === docId && model && yjs.ytext.toString() === model.getValue());
        }""",
        arg=doc_id,
        timeout=60000,
    )


def set_text(page: Page, text: str) -> None:
    page.evaluate("(t) => window.monaco.editor.getEditors()[0].setValue(t)", text)


def still_over(page: Page, count: int) -> None:
    page.wait_for_function(
        """(count) => {
            const boxes = Array.from(document.querySelectorAll('[data-embed-kind=drawing]'));
            const frames = Array.from(document.querySelectorAll('#embed-layer iframe'));
            return boxes.length === count && frames.length === count && boxes.every((b) => frames.some((f) =>
                f.src === b.dataset.embedSrc && Math.abs(b.getBoundingClientRect().top - f.getBoundingClientRect().top) < 1));
        }""",
        arg=count,
        timeout=8000,
    )


def heights(page: Page) -> list:
    return page.evaluate(
        """() => Array.from(document.querySelectorAll('[data-embed-kind=drawing]')).map((b) => {
            const r = b.getBoundingClientRect();
            return [Math.round(r.width), Math.round(r.height)];
        })"""
    )


def run() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    port = urlparse(VECDRAW_URL).port
    server = ThreadingHTTPServer(("127.0.0.1", port), Stand)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    doc_id = "vecdraw-embed-" + uuid.uuid4().hex[:8]
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS)
        page = browser.new_context(viewport={"width": 1400, "height": 900}).new_page()
        page.set_default_timeout(TIMEOUT_MS)
        page.goto(f"{BASE_URL}/doc/{doc_id}")
        page.wait_for_selector(".monaco-editor textarea", state="attached", timeout=90000)
        wait_bound(page, doc_id)

        # 1
        set_text(page, "# Doc\n\nAbove.\n\n{%vecdraw wide %}\n\nBetween.\n\n{%vecdraw https://vecdraw.example.com/doc/tall/ %}\n\nBelow.\n")
        still_over(page, 2)
        page.wait_for_timeout(400)
        assert loads == {"wide": 1, "tall": 1}, f"one load each: {loads}"
        assert page.locator("#embed-layer iframe").first.get_attribute("title") == "Codoc in VecDraw"
        assert page.evaluate("() => document.querySelectorAll('#preview-pane [data-embed-src] iframe').length") == 0, "the document holds no frame"
        assert not page.locator("[data-embed-kind=drawing] img").first.is_visible(), "the picture is for printing"
        page.screenshot(path=str(OUTPUT_DIR / "frames.png"))

        # 2
        page.wait_for_function("() => document.querySelector('[data-embed-kind=drawing]').getBoundingClientRect().height > 96")
        (width, height), (_, tall) = heights(page)
        assert abs(height - width * 0.5) <= 1, heights(page)
        assert tall == 900 * 0.7, heights(page)
        page.set_viewport_size({"width": 1000, "height": 900})
        page.wait_for_function("(w) => document.querySelector('[data-embed-kind=drawing]').getBoundingClientRect().width < w", arg=width)
        page.wait_for_timeout(300)
        still_over(page, 2)
        (width, height), _ = heights(page)
        assert abs(height - width * 0.5) <= 1, f"the box follows the pane: {heights(page)}"
        page.set_viewport_size({"width": 1400, "height": 900})

        # 3
        ed = "window.monaco.editor.getEditors()[0]"
        page.evaluate(f"() => {{ {ed}.setPosition({{lineNumber: 3, column: 1}}); {ed}.focus(); }}")
        page.keyboard.type("A word.", delay=5)
        page.keyboard.press("Enter")
        page.keyboard.press("Enter")
        page.keyboard.type("A new paragraph.", delay=5)
        page.keyboard.press("Enter")
        page.keyboard.press("Enter")
        page.wait_for_function("() => document.getElementById('preview-pane').innerText.includes('A new paragraph.')")
        still_over(page, 2)
        assert loads == {"wide": 1, "tall": 1}, f"edits reloaded a frame: {loads}"

        # 4
        set_text(page, "# Doc\n\n{%vecdraw no/such thing %}\n\nBelow.\n")
        page.wait_for_function("() => document.getElementById('preview-pane').innerText.includes('{%vecdraw no/such thing %}')")
        page.wait_for_function("() => document.querySelectorAll('[data-embed-kind=drawing]').length === 0")

        # 5
        set_text(page, "# Doc\n\n{%vecdraw wide %}\n\nBelow.\n")
        still_over(page, 1)
        page.emulate_media(media="print")
        assert page.locator("[data-embed-kind=drawing] img").is_visible(), "a printed page has the picture"
        assert not page.locator("#embed-layer").is_visible()
        page.emulate_media(media="screen")
        browser.close()
    print("PASS")


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL: {exc}")
        sys.exit(1)
