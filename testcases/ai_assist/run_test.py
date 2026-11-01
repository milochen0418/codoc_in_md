"""E2E: the AI on a document, in real browsers with real Yjs and Monaco.

A stand-in for the AI Hub runs here (it speaks reflex_ddns_auth.ai's wire and shows a page for the
assistant's dialog); the tools are called the way the hub calls them. Run it with

    DDNS_AI_HUB_URL=http://127.0.0.1:8397 DDNS_INTENT_URL_AI=http://127.0.0.1:8397 \
    DDNS_INTENT_PROVIDER_AI_ASSIST=ai DDNS_INTENT_PROVIDER_AI_TALK=ai DDNS_INTENT_TRUST_LOCALHOST=1 \
    DDNS_AUTH_SECRET=<32 characters or more> poetry run ./run_test_suite.sh ai_assist

1. md.read gives what is in the editor; an unsigned call is refused.
2. md.edit reaches both people's editors, Chinese and emoji included, marked in the AI's color with
   its name, and is saved. The AI shows among the people for a moment.
3. Someone typing while the AI changes the text keeps what they typed.
4. The note on the document takes the change back for everyone, with what was typed since. It goes
   for both people, and a note one dismissed stays with the other.
5. A change people wrote over can't be taken back, and says so.
6. md.append adds at the end; md.rewrite replaces it all; md.create makes a document that opens.
7. The writer: Cmd/Ctrl+I on a selection, a quick button, the answer as it streams, then as a change;
   Replace goes in as the person's own edit (the other person gets it, Ctrl+Z takes it back).
8. Esc while it writes stops it; Esc on an answer discards it, and nothing changed.
9. Insert below keeps the selection. The small button on a selection opens the writer too.
10. At the caret: the writer offers to continue, and the answer goes in there.
11. Text added above while the AI writes: the answer still goes in its place. Text changed inside the
    selection: it is refused, and nothing changes.
12. A failing hub shows in the writer.
13. What the page tells the assistant; Alt+A from the editor opens it on this document, Talk the talking AI.
14. Preview Only has no writer; a change still reaches it.
"""

import json
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.request
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
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")
HUB_URL = os.getenv("DDNS_AI_HUB_URL", "http://127.0.0.1:8397").rstrip("/")
SECRET = os.getenv("DDNS_AUTH_SECRET", "")
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "testcases/ai_assist/output"))
HEADLESS = env_bool("HEADLESS", True)
SLOWMO = int(os.getenv("PW_SLOWMO_MS", "0"))
TIMEOUT_MS = int(os.getenv("PW_TIMEOUT_MS", "30000"))
MOD = "Meta" if sys.platform == "darwin" else "Control"
AI_COLOR = "rgb(124, 58, 237)"
MODEL = "Stand-in"


class Hub:
    asks: list[dict] = []
    fail = ""
    delay = 0.04
    opened: list[str] = []  # the assistant's dialog: the addresses it was opened at


class Stand(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _json(self, data: dict, status: int = 200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/ai/status":
            return self._json({"ok": True, "model": MODEL, "provider": "stand-in", "local": True})
        Hub.opened.append(self.path)
        body = b"<!doctype html><title>AI</title><body>The assistant</body>"
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        ask = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        Hub.asks.append(ask)
        if Hub.fail:
            return self._json({"error": Hub.fail}, 503)
        first, last = ask["messages"][0]["content"], ask["messages"][-1]["content"]
        part = re.search(r"<<<\n(.*)\n>>>", first, re.S)
        if "Translate" in last:
            answer = "翻譯結果"
        elif part:
            answer = part.group(1).upper()
        else:
            answer = "Words at the caret."
        self.send_response(200)
        self.send_header("Content-Type", "application/x-ndjson")
        self.end_headers()
        self.wfile.write((json.dumps({"model": MODEL}) + "\n").encode())
        try:
            for i in range(0, len(answer), 2):
                self.wfile.write((json.dumps({"text": answer[i:i + 2]}) + "\n").encode())
                self.wfile.flush()
                time.sleep(Hub.delay)
            self.wfile.write((json.dumps({"done": True, "stop": "end_turn"}) + "\n").encode())
        except OSError:
            pass  # the app stopped listening: Stop


page_errors: list[str] = []


def token() -> str:
    import jwt

    now = int(time.time())
    return jwt.encode({"iss": "ai-hub", "aud": "ddns-tool", "app": "md", "sub": "assistant", "iat": now, "exp": now + 300, "jti": uuid.uuid4().hex}, SECRET, algorithm="HS256")


def call(name: str, signed: bool = True, **args) -> dict:
    """Calls a tool the way the AI Hub does."""
    request = urllib.request.Request(f"{BACKEND_URL}/_ddns_tool/call/{name}", json.dumps({"args": args}).encode(), {"Content-Type": "application/json"})
    if signed:
        request.add_header("Authorization", f"Bearer {token()}")
    try:
        with urllib.request.urlopen(request, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        return {"status": e.code, **json.load(e)}


def result(name: str, **args):
    out = call(name, **args)
    assert out.get("ok"), f"{name} failed: {out}"
    return out["result"]


def open_doc(context, url: str) -> Page:
    page = context.new_page()
    page.set_default_timeout(TIMEOUT_MS)

    def on_error(err):
        # Reflex's own window.onerror reads a null error; harmless, and not ours.
        if "reading 'name'" not in str(err):
            page_errors.append(str(err))

    page.on("pageerror", on_error)
    page.goto(url, wait_until="domcontentloaded")
    page.locator("#editor-pane .monaco-editor").wait_for(state="visible", timeout=60000)
    page.wait_for_function(
        """() => {
            const yjs = window._codocYjs;
            const ed = window.monaco && window.monaco.editor.getEditors()[0];
            const me = yjs && yjs.provider.awareness.getLocalState();
            return !!(me && me.user && ed && ed.getValue() && yjs.ytext.length && window.codocAi);
        }""",
        timeout=60000,
    )
    return page


def text_of(page: Page) -> str:
    return page.evaluate("() => window.monaco.editor.getEditors()[0].getValue()")


def wait_text(page: Page, wanted: str) -> None:
    page.wait_for_function("(t) => window.monaco.editor.getEditors()[0].getValue() === t", arg=wanted, polling=100)


def set_text(page: Page, text: str) -> None:
    page.evaluate("(t) => window.monaco.editor.getEditors()[0].getModel().setValue(t)", text)


def select(page: Page, words: str) -> None:
    """Selects these words in the editor, and goes there."""
    page.evaluate(
        """(words) => {
            const ed = window.monaco.editor.getEditors()[0];
            const model = ed.getModel();
            const at = model.getValue().indexOf(words);
            const a = model.getPositionAt(at), b = model.getPositionAt(at + words.length);
            ed.focus();
            ed.setSelection(new window.monaco.Selection(a.lineNumber, a.column, b.lineNumber, b.column));
        }""",
        words,
    )


def caret_after(page: Page, words: str) -> None:
    page.evaluate(
        """(words) => {
            const ed = window.monaco.editor.getEditors()[0];
            const model = ed.getModel();
            ed.focus();
            ed.setPosition(model.getPositionAt(model.getValue().indexOf(words) + words.length));
        }""",
        words,
    )


def open_writer(page: Page) -> None:
    page.keyboard.press(f"{MOD}+i")
    page.locator("#ai-writer").wait_for(state="visible")
    page.wait_for_function("() => document.activeElement && document.activeElement.id === 'ai-request'")


def saved(doc_id: str) -> str:
    return result("md.read", room=doc_id)["text"]


def wait_saved(doc_id: str, wanted: str, seconds: float = 8.0) -> None:
    deadline = time.time() + seconds
    while time.time() < deadline:
        if saved(doc_id) == wanted:
            return
        time.sleep(0.1)
    raise AssertionError(f"saved text is {saved(doc_id)!r}, not {wanted!r}")


def main() -> int:
    assert SECRET, "DDNS_AUTH_SECRET must be set, the same as the server's"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    port = urlparse(HUB_URL).port or 8397
    hub = ThreadingHTTPServer(("127.0.0.1", port), Stand)
    threading.Thread(target=hub.serve_forever, daemon=True).start()
    doc_id = f"ai{uuid.uuid4().hex[:6]}"
    url = f"{BASE_URL}/doc/{doc_id}"
    shots: dict[str, bytes] = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS, slow_mo=SLOWMO)
        try:
            amy = open_doc(browser.new_context(viewport={"width": 1440, "height": 900}), url)
            ben = open_doc(browser.new_context(viewport={"width": 1440, "height": 900}), url)
            start = "# 專案週報 😀\n\n這個禮拜我們把登入的功能做完了。\n\nThe release is in May.\n\n## Next\n\n- Finish the tests\n"
            set_text(amy, start)
            wait_text(ben, start)
            wait_saved(doc_id, start)

            print("1. md.read gives what is in the editor; an unsigned call is refused...")
            read = result("md.read", room=doc_id)
            assert read["text"] == start and read["title"] == "專案週報 😀" and read["lines"] == 10, read
            assert result("md.read", room=doc_id, from_line=5, to_line=5)["text"] == "The release is in May."
            refused = call("md.read", signed=False, room=doc_id)
            assert refused.get("status") == 401 and not refused.get("ok"), refused
            assert doc_id in [d["room"] for d in result("md.list_documents", search="專案週報")["documents"]]
            assert "md_edit" in result("md.guide")

            print("2. md.edit reaches both people's editors, marked in the AI's color...")
            out = result("md.edit", room=doc_id, summary="改成六月", edits=[{"find": "The release is in May.", "replace": "發布在六月 🎉，很順利。"}, {"find": "登入的功能", "replace": "登入功能 🔐"}])
            assert out["changed"] == 2 and out["first_changed_line"] == 3, out
            after = "# 專案週報 😀\n\n這個禮拜我們把登入功能 🔐做完了。\n\n發布在六月 🎉，很順利。\n\n## Next\n\n- Finish the tests\n"
            wait_text(amy, after)
            wait_text(ben, after)
            wait_saved(doc_id, after)
            for page in (amy, ben):
                mark = page.locator(".yRemoteSelection").first
                mark.wait_for(state="attached")
                color = page.locator(".yRemoteSelectionHead").first.evaluate("el => getComputedStyle(el).borderLeftColor")
                assert color == AI_COLOR, color
                assert page.locator(".codoc-cursor-tag", has_text="AI").count() == 1
                page.wait_for_function("() => [...document.querySelectorAll('header img')].some(i => i.alt === 'AI')")
            # The mark covers what the AI wrote, and nothing else: Yjs counts an emoji as two.
            marked = amy.evaluate(
                """() => {
                    const ed = window.monaco.editor.getEditors()[0];
                    const model = ed.getModel();
                    const found = model.getAllDecorations().find((d) => (d.options.className || '').startsWith('yRemoteSelection'));
                    return found ? model.getValueInRange(found.range) : null;
                }"""
            )
            assert marked == "功能 🔐", f"the mark is on {marked!r}"
            shots["2_marked"] = amy.screenshot()
            amy.locator(".ai-note").wait_for(state="visible")
            assert "改成六月" in amy.locator(".ai-note-text").inner_text()
            amy.wait_for_function("() => !document.querySelector('.yRemoteSelection')", timeout=12000)

            print("3. Someone typing while the AI changes the text keeps what they typed...")
            caret_after(ben, "- Finish the tests")
            ben.keyboard.type(" and ship", delay=25)
            result("md.edit", room=doc_id, summary="改標題", edits=[{"find": "## Next", "replace": "## 下一步"}])
            ben.keyboard.type(" it", delay=25)
            merged = after.replace("## Next", "## 下一步").replace("- Finish the tests", "- Finish the tests and ship it")
            wait_text(amy, merged)
            wait_text(ben, merged)

            print("4. The note takes the change back for everyone, with what was typed since...")
            amy.locator(".ai-note", has_text="改標題").locator(".ai-note-undo").click()
            undone = merged.replace("## 下一步", "## Next")
            wait_text(amy, undone)
            wait_text(ben, undone)
            wait_saved(doc_id, undone)
            for page in (amy, ben):
                page.wait_for_function("() => document.querySelectorAll('.ai-note').length === 1")
            amy.locator(".ai-note-close").click()
            amy.wait_for_function("() => !document.querySelector('.ai-note')")
            time.sleep(1.2)
            assert ben.locator(".ai-note").count() == 1, "a note one person dismissed stays with the other"
            assert amy.locator(".ai-note").count() == 0, "a dismissed note stays away"

            print("5. A change people wrote over can't be taken back, and says so...")
            before = text_of(ben)
            select(ben, "六月")
            ben.keyboard.type("七月")
            typed_over = before.replace("六月", "七月")
            wait_text(amy, typed_over)
            ben.locator(".ai-note-undo").click()
            ben.get_by_text("so it can't be taken back").wait_for()
            assert text_of(amy) == typed_over

            print("6. md.append adds at the end; md.rewrite replaces it all; md.create makes a document that opens...")
            result("md.append", room=doc_id, summary="加上結語", text="## 結語\n\n謝謝大家。")
            ending = typed_over + "\n## 結語\n\n謝謝大家。"
            wait_text(amy, ending)
            result("md.rewrite", room=doc_id, summary="全部重寫", text="# 全新內容\n")
            wait_text(ben, "# 全新內容\n")
            amy.locator(".ai-note", has_text="全部重寫").locator(".ai-note-undo").click()
            wait_text(ben, ending)
            made = result("md.create", title="新文件", text="第一段")
            assert saved(made["room"]) == "# 新文件\n\n第一段\n"
            other = open_doc(browser.new_context(), f"{BASE_URL}/doc/{made['room']}")
            assert text_of(other) == "# 新文件\n\n第一段\n"
            other.context.close()

            print("7. The writer: a quick button, the answer as it streams, then as a change...")
            set_text(amy, start)
            wait_text(ben, start)
            select(amy, "The release is in May.")
            Hub.delay = 0.12
            Hub.asks.clear()
            open_writer(amy)
            assert amy.locator("#ai-where").inner_text() == "22 characters selected"
            box = amy.locator("#ai-writer").bounding_box()
            line = amy.evaluate(
                """() => {
                    const ed = window.monaco.editor.getEditors()[0];
                    const p = ed.getScrolledVisiblePosition(ed.getSelection().getEndPosition());
                    return ed.getDomNode().getBoundingClientRect().top + p.top;
                }"""
            )
            assert box["y"] > line, f"the writer is under the selection ({box['y']} > {line})"
            amy.wait_for_function("() => document.querySelector('.codoc-ai-target')")
            shots["7_ready"] = amy.screenshot()
            amy.locator('[data-quick="improve"]').click()
            amy.wait_for_function("() => { const a = document.getElementById('ai-answer'); return a && a.textContent.length > 0 && a.textContent.length < 22; }")
            assert amy.locator("#ai-stop").is_visible()
            amy.locator("#ai-accept").wait_for(state="visible")
            Hub.delay = 0.04
            assert amy.locator("#ai-answer span.bg-emerald-100").first.inner_text() != ""
            assert amy.locator("#ai-model").inner_text() == MODEL
            ask = Hub.asks[-1]
            assert ask["role"] == "fast" and ask["max_tokens"] >= 8000 and "The release is in May." in ask["messages"][0]["content"], ask
            assert "登入的功能" in ask["messages"][0]["content"], "the text around the selection goes with it"
            shots["7_answer"] = amy.screenshot()
            amy.keyboard.press(f"{MOD}+Enter")
            amy.locator("#ai-writer").wait_for(state="detached")
            replaced = start.replace("The release is in May.", "THE RELEASE IS IN MAY.")
            wait_text(amy, replaced)
            wait_text(ben, replaced)
            amy.keyboard.press(f"{MOD}+z")
            wait_text(amy, start)
            wait_text(ben, start)

            print("8. Esc stops it, and discards an answer; nothing changed...")
            select(amy, "Finish the tests")
            open_writer(amy)
            Hub.delay = 0.3
            amy.locator("#ai-request").fill("do it")
            amy.keyboard.press("Enter")
            amy.locator("#ai-stop").wait_for(state="visible")
            amy.keyboard.press("Escape")
            amy.locator("#ai-stop").wait_for(state="detached")
            assert amy.locator("#ai-writer").is_visible(), "Esc while it writes stops it; the writer stays"
            Hub.delay = 0.02
            amy.locator("#ai-request").fill("again")
            amy.keyboard.press("Enter")
            amy.locator("#ai-accept").wait_for(state="visible")
            amy.keyboard.press("Escape")
            amy.locator("#ai-writer").wait_for(state="detached")
            amy.wait_for_function("() => !document.querySelector('.codoc-ai-target')")
            assert text_of(amy) == start

            print("9. Insert below keeps the selection; the small button opens the writer too...")
            select(amy, "Finish the tests")
            amy.locator("#ai-chip").wait_for(state="visible")
            shots["9_chip"] = amy.screenshot()
            amy.locator("#ai-chip").click()
            amy.locator("#ai-writer").wait_for(state="visible")
            amy.locator('[data-quick="english"]').click()
            amy.locator("#ai-below").wait_for(state="visible")
            assert amy.locator("#ai-answer").inner_text() == "翻譯結果", "a translation shows as it is, not as a change"
            amy.locator("#ai-below").click()
            below = start.replace("- Finish the tests", "- Finish the tests\n\n翻譯結果")
            wait_text(ben, below)
            set_text(amy, start)
            wait_text(ben, start)

            print("10. At the caret: the writer offers to continue, and the answer goes in there...")
            caret_after(amy, "這個禮拜我們把登入的功能做完了。")
            open_writer(amy)
            assert amy.locator("#ai-where").inner_text() == "At the caret, line 3"
            assert amy.locator('[data-quick="improve"]').count() == 0
            amy.locator('[data-quick="continue"]').click()
            amy.locator("#ai-accept").click()
            amy.locator("#ai-writer").wait_for(state="detached")
            wait_text(ben, start.replace("做完了。", "做完了。Words at the caret."))
            set_text(amy, start)
            wait_text(ben, start)

            print("11. Text added above while the AI writes: the answer still goes in its place...")
            select(amy, "Finish the tests")
            open_writer(amy)
            amy.locator("#ai-request").fill("upper case")
            amy.keyboard.press("Enter")
            amy.locator("#ai-accept").wait_for(state="visible")
            result("md.append", room=doc_id, summary="加前言", text="前言", at="start")
            shifted = "前言\n\n" + start
            wait_text(amy, shifted)
            amy.locator("#ai-accept").click()
            amy.locator("#ai-writer").wait_for(state="detached")
            wait_text(ben, shifted.replace("Finish the tests", "FINISH THE TESTS"))
            select(amy, "FINISH THE TESTS")
            open_writer(amy)
            amy.locator("#ai-request").fill("upper case")
            amy.keyboard.press("Enter")
            amy.locator("#ai-accept").wait_for(state="visible")
            changed = shifted.replace("Finish the tests", "FINISH ALL THE TESTS")
            result("md.edit", room=doc_id, summary="改一個字", edits=[{"find": "FINISH THE TESTS", "replace": "FINISH ALL THE TESTS"}])
            wait_text(amy, changed)
            amy.locator("#ai-accept").click()
            amy.locator("#ai-error").wait_for(state="visible")
            assert "changed while the AI was writing" in amy.locator("#ai-error").inner_text()
            assert text_of(amy) == changed
            amy.locator("#ai-close").click()
            amy.locator("#ai-writer").wait_for(state="detached")

            print("12. A failing hub shows in the writer...")
            Hub.fail = "Nothing answers this role"
            select(amy, "前言")
            open_writer(amy)
            amy.locator('[data-quick="fix"]').click()
            amy.locator("#ai-error").wait_for(state="visible")
            assert "Nothing answers this role" in amy.locator("#ai-error").inner_text()
            Hub.fail = ""
            amy.keyboard.press("Escape")
            amy.locator("#ai-writer").wait_for(state="detached")

            print("13. What the page tells the assistant; the AI menu opens it on this document...")
            select(amy, "前言")
            context = amy.evaluate("() => window.__ddnsContext()")
            assert f"(room {doc_id})" in context["text"] and "lines 1 to 1: 前言" in context["text"], context
            caret_after(amy, "前言")
            context = amy.evaluate("() => window.__ddnsContext()")
            assert "The caret is on line 1: 前言" in context["text"], context
            Hub.opened.clear()
            amy.keyboard.press("Alt+a")
            amy.wait_for_function("() => document.querySelector('iframe[src*=\"ai\"], iframe[src*=\"8397\"], iframe[src*=\"assist\"]')")
            src = amy.evaluate("() => [...document.querySelectorAll('iframe')].map(f => f.src).find(s => s.includes('in_app'))")
            assert "in_app=md" in src and f"room={doc_id}" in src, src
            assert text_of(amy).startswith("前言"), "Alt+A typed nothing"
            shots["13_assistant"] = amy.screenshot()
            amy.get_by_role("button", name="Close", exact=True).first.click()
            amy.wait_for_function("() => ![...document.querySelectorAll('iframe')].some(f => f.src.includes('ai-assist'))")
            ben.get_by_role("button", name="AI", exact=True).hover()
            ben.locator("#ai-talk").click()
            ben.wait_for_function("() => [...document.querySelectorAll('iframe')].some(f => f.src.includes('in_app=md') && f.src.includes('talk'))")
            src = ben.evaluate("() => [...document.querySelectorAll('iframe')].map(f => f.src).find(s => s.includes('talk'))")
            assert f"room={doc_id}" in src, src
            ben.get_by_role("button", name="Close", exact=True).first.click()
            ben.wait_for_function("() => ![...document.querySelectorAll('iframe')].some(f => f.src.includes('talk'))")

            print("14. Preview Only has no writer; a change still reaches it...")
            ben.locator('button[title="Preview Only"]').click()
            ben.locator("#preview-pane").wait_for(state="visible")
            ben.get_by_role("button", name="AI", exact=True).hover()
            ben.locator("#ai-assist").wait_for(state="visible")
            assert ben.locator("#ai-rewrite").count() == 0
            ben.keyboard.press(f"{MOD}+i")
            time.sleep(0.5)
            assert ben.locator("#ai-writer").count() == 0
            result("md.append", room=doc_id, summary="預覽看得到", text="預覽看得到這一行")
            ben.get_by_text("預覽看得到這一行").first.wait_for(state="visible")

            assert not page_errors, f"page errors: {page_errors}"
            print("PASS")
            return 0
        except Exception:
            for name, page in (("amy", locals().get("amy")), ("ben", locals().get("ben"))):
                if page is not None:
                    try:
                        (OUTPUT_DIR / f"failure_{name}.png").write_bytes(page.screenshot())
                    except Exception:
                        pass
            raise
        finally:
            # Written at the end: a new file under testcases/ restarts a dev server.
            for name, data in shots.items():
                (OUTPUT_DIR / f"{name}.png").write_bytes(data)
            browser.close()
            hub.shutdown()


if __name__ == "__main__":
    sys.exit(main())
