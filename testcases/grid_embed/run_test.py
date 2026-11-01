"""E2E: frames in the preview (ReflexGrid's forms and tables) stand still while the document changes.

A stand-in for ReflexGrid serves two pages here, so the suite needs no other app, and counts how often
each is loaded. Run it with

    DDNS_INTENT_URL_GRID=http://127.0.0.1:8398 poetry run ./run_test_suite.sh grid_embed

1. A document with a form and a table: each frame loads once, over its box.
2. A frame says how tall it is: the box follows, and what is below it moves down. A long table stops
   at 70% of the window. A frame can't size another one, and neither can the page around it.
3. Typing and new blocks above a frame move it with its box and don't reload it: what was typed
   in the form stays, also when someone else makes the change.
4. A line being typed loads nothing until it stands still, and only once.
5. Removing the line removes the frame.
6. Preview Only and back: the frames are there again, over their boxes.
7. codocInsertBlock puts a line at the caret, on lines of its own; in Preview Only at the end.
"""

import json
import os
import sys
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import Page, sync_playwright


def env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:3000").rstrip("/")
GRID_URL = os.getenv("DDNS_INTENT_URL_GRID", "").rstrip("/")
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "testcases/grid_embed/output"))
HEADLESS = env_bool("HEADLESS", True)
SLOWMO = int(os.getenv("PW_SLOWMO_MS", "0"))
TIMEOUT_MS = int(os.getenv("PW_TIMEOUT_MS", "30000"))

PAGE = """<!doctype html><html><body style="margin:0;font:13px sans-serif">
<input id="field"><div id="what">%s</div>
<script>
window.say = (height) => parent.postMessage({type: "reflex-grid-embed", height}, "*");
window.reach = (height) => { for (const f of parent.frames) f.postMessage({type: "x"}, "*"); };
say(%d);
</script></body></html>"""

loads: dict[str, int] = {}


class Stand(BaseHTTPRequestHandler):
    def do_GET(self):
        url = urlparse(self.path)
        q = parse_qs(url.query)
        what = (q.get("form") or q.get("range") or ["?"])[0]
        if url.path not in ("/intent/grid-form", "/_reflex_grid/embed/table"):
            self.send_error(404)
            return
        loads[what] = loads.get(what, 0) + 1
        body = (PAGE % (what, 150)).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
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


def frame(page: Page, what: str):
    for _ in range(100):
        for f in page.frames:
            if f.url.endswith("=" + what):
                return f
        page.wait_for_timeout(100)
    raise AssertionError(f"no frame for {what}: {[f.url for f in page.frames]}")


def placed(page: Page) -> list:
    """For each box: how far its frame is from it (top, left, width, height), and its height."""
    return page.evaluate(
        """() => Array.from(document.querySelectorAll('[data-embed-src]')).map((b, i) => {
            const f = document.querySelectorAll('#embed-layer iframe')[i];
            const r = b.getBoundingClientRect(), q = f.getBoundingClientRect();
            return [Math.round(r.top - q.top), Math.round(r.left - q.left), Math.round(r.width - q.width), Math.round(r.height - q.height), Math.round(r.height)];
        })"""
    )


def still_over(page: Page, count: int) -> None:
    page.wait_for_function(
        """(count) => {
            const boxes = Array.from(document.querySelectorAll('[data-embed-src]'));
            const frames = Array.from(document.querySelectorAll('#embed-layer iframe'));
            return boxes.length === count && frames.length === count && boxes.every((b) => {
                const f = frames.find((x) => x.src === b.dataset.embedSrc);
                return f && Math.abs(b.getBoundingClientRect().top - f.getBoundingClientRect().top) < 1;
            });
        }""",
        arg=count,
        timeout=8000,
    )


def run() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    port = urlparse(GRID_URL).port
    server = ThreadingHTTPServer(("127.0.0.1", port), Stand)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    doc_id = "grid-embed-" + uuid.uuid4().hex[:8]
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS, slow_mo=SLOWMO)
        writer = browser.new_context(viewport={"width": 1400, "height": 900}).new_page()
        other = browser.new_context(viewport={"width": 1400, "height": 900}).new_page()
        for page in (writer, other):
            page.set_default_timeout(TIMEOUT_MS)
            page.goto(f"{BASE_URL}/doc/{doc_id}")
            page.wait_for_selector(".monaco-editor textarea", state="attached", timeout=90000)
            wait_bound(page, doc_id)

        # 1
        set_text(writer, "# Doc\n\nAbove.\n\n{%grid b1 form=F %}\n\nBetween.\n\n{%grid b1 range=T %}\n\nBelow.\n")
        form, table = frame(writer, "F"), frame(writer, "T")
        still_over(writer, 2)
        writer.wait_for_timeout(400)
        assert loads == {"F": 2, "T": 2}, f"one load each, in two tabs: {loads}"
        assert writer.evaluate("() => document.querySelectorAll('#preview-pane [data-embed-src] iframe').length") == 0, "the document holds no frame"
        writer.screenshot(path=str(OUTPUT_DIR / "frames.png"))

        # 2
        tops = lambda: writer.evaluate("() => Array.from(document.querySelectorAll('[data-embed-src]')).map((b) => b.getBoundingClientRect().top)")
        assert [row[4] for row in placed(writer)] == [150, 150], placed(writer)
        before = tops()
        form.evaluate("() => say(260)")
        writer.wait_for_function("() => document.querySelector('[data-embed-kind=form]').getBoundingClientRect().height === 260")
        still_over(writer, 2)
        assert tops()[1] - before[1] == 110, "what is below moved down"
        table.evaluate("() => say(5000)")
        writer.wait_for_function("(h) => document.querySelector('[data-embed-kind=table]').getBoundingClientRect().height === h", arg=900 * 0.7)
        table.evaluate("() => say(150)")
        writer.evaluate("""() => window.postMessage({type: "reflex-grid-embed", height: 999}, "*")""")
        writer.wait_for_timeout(300)
        assert placed(writer)[0][4] == 260 and placed(writer)[1][4] == 150, placed(writer)

        # 3
        form.locator("#field").fill("half typed")
        table.locator("#field").fill("marker")
        ed = "window.monaco.editor.getEditors()[0]"
        writer.evaluate(f"() => {{ {ed}.setPosition({{lineNumber: 3, column: 1}}); {ed}.focus(); }}")
        writer.keyboard.type("A word. ", delay=5)
        writer.keyboard.press("Enter")
        writer.keyboard.press("Enter")
        writer.keyboard.type("A new paragraph.", delay=5)
        writer.keyboard.press("Enter")
        writer.keyboard.press("Enter")
        other.evaluate(f"() => {{ {ed}.setPosition({{lineNumber: 1, column: 1}}); {ed}.focus(); }}")
        other.keyboard.type("# First", delay=5)
        other.keyboard.press("Enter")
        other.keyboard.press("Enter")
        other.keyboard.type("> A quote.", delay=5)
        other.keyboard.press("Enter")
        other.keyboard.press("Enter")
        writer.wait_for_function("() => document.getElementById('preview-pane').innerText.includes('A quote.')")
        still_over(writer, 2)
        assert loads == {"F": 2, "T": 2}, f"edits reloaded a frame: {loads}"
        assert form.locator("#field").input_value() == "half typed"
        assert table.locator("#field").input_value() == "marker"

        # 4
        before = dict(loads)
        writer.evaluate(f"() => {{ const e = {ed}; const m = e.getModel(); e.setPosition(m.getFullModelRange().getEndPosition()); e.focus(); }}")
        writer.keyboard.press("Enter")
        writer.keyboard.press("Enter")
        writer.evaluate(f"""() => {{ const e = {ed}; const at = e.getPosition();
            e.executeEdits("t", [{{range: new window.monaco.Range(at.lineNumber, at.column, at.lineNumber, at.column), text: "{{%grid b1 range=Wa %}}"}}]); }}""")
        for suffix in ("Wat", "Wate", "Water"):
            writer.wait_for_timeout(120)
            writer.evaluate(f"""(s) => {{ const m = {ed}.getModel(); const n = m.getLineCount();
                const old = m.getLineContent(n); const at = old.indexOf("range=") + 6; const end = old.indexOf(" %}}");
                m.applyEdits([{{range: new window.monaco.Range(n, at + 1, n, end + 1), text: s}}]); }}""", suffix)
        frame(writer, "Water")
        writer.wait_for_timeout(1000)
        assert loads.get("Water") == 2 and "Wa" not in loads and "Wat" not in loads and "Wate" not in loads, f"{loads}"

        # 5
        writer.evaluate(f"""() => {{ const m = {ed}.getModel(); const n = m.getLineCount();
            m.applyEdits([{{range: new window.monaco.Range(n, 1, n, m.getLineMaxColumn(n)), text: ""}}]); }}""")
        writer.wait_for_function("() => document.querySelectorAll('#embed-layer iframe').length === 2", timeout=8000)

        # 6
        writer.locator('button[title="Preview Only"]').click()
        writer.wait_for_function("() => document.querySelector('#editor-pane.hidden') && document.querySelectorAll('#embed-layer iframe').length === 2", timeout=8000)
        still_over(writer, 2)
        writer.locator('button[title="Split View"]').click()
        writer.wait_for_function("() => !document.querySelector('#editor-pane.hidden') && document.querySelectorAll('#embed-layer iframe').length === 2", timeout=8000)
        still_over(writer, 2)

        # 7
        set_text(writer, "one\ntwo\n")
        writer.evaluate(f"() => {{ {ed}.setPosition({{lineNumber: 1, column: 4}}); {ed}.focus(); }}")
        writer.evaluate("() => window.codocInsertBlock('{%grid b1 range=X %}')")
        assert writer.evaluate(f"() => {ed}.getValue()") == "one\n\n{%grid b1 range=X %}\n\ntwo\n"
        writer.evaluate(f"() => {ed}.setPosition({{lineNumber: 1, column: 2}})")
        writer.evaluate("() => window.codocInsertBlock('{%grid b1 range=Y %}')")
        assert writer.evaluate(f"() => {ed}.getValue()").startswith("o\n\n{%grid b1 range=Y %}\n\nne\n")
        writer.locator('button[title="Preview Only"]').click()
        writer.wait_for_selector("#editor-pane.hidden", state="attached")
        writer.evaluate("() => window.codocInsertBlock('{%grid b1 range=Z %}')")
        assert writer.evaluate(f"() => {ed}.getValue()").endswith("{%grid b1 range=Z %}\n"), writer.evaluate(f"() => {ed}.getValue()")
        browser.close()
    server.shutdown()
    print("[grid_embed] PASS", json.dumps(loads))


if __name__ == "__main__":
    if not GRID_URL:
        print("[grid_embed] needs DDNS_INTENT_URL_GRID, see the top of this file")
        sys.exit(2)
    run()
