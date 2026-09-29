"""Regression: editing doc A, going back to My Documents and opening doc B
must not leak A's content into B (stale Reflex state / Yjs binding)."""

import os
import sys
import time
import uuid
from pathlib import Path

from playwright.sync_api import sync_playwright


def env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def _editor_value(page) -> str:
    return page.evaluate(
        """() => {
            const eds = (window.monaco && window.monaco.editor.getEditors()) || [];
            return eds.length ? eds[0].getModel().getValue() : '';
        }"""
    )


def _wait_editor_contains(page, text: str) -> None:
    page.wait_for_function(
        """(t) => {
            const eds = (window.monaco && window.monaco.editor.getEditors()) || [];
            return eds.length && eds[0].getModel() && eds[0].getModel().getValue().includes(t);
        }""",
        arg=text,
    )


def main() -> int:
    base_url = os.getenv("BASE_URL", "http://127.0.0.1:3000").rstrip("/")
    output_dir = Path(os.getenv("OUTPUT_DIR", "testcases/doc_switch_no_leak/output"))
    output_dir.mkdir(parents=True, exist_ok=True)

    headless = env_bool("HEADLESS", True)
    timeout_ms = int(os.getenv("PW_TIMEOUT_MS", "30000"))

    suffix = uuid.uuid4().hex[:6]
    doc_a, doc_b = f"leakA{suffix}", f"leakB{suffix}"
    title_b = f"Doc B {suffix}"
    marker_a = f"SECRET_A_{suffix}"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(viewport={"width": 1280, "height": 720})
        page = context.new_page()
        page.set_default_timeout(timeout_ms)

        try:
            # Create doc B with its own content.
            page.goto(f"{base_url}/doc/{doc_b}", wait_until="domcontentloaded")
            _wait_editor_contains(page, "Start typing")
            time.sleep(3)  # let Yjs finish the first-client seed
            page.locator("#editor-pane .monaco-editor").first.click()
            page.keyboard.press("Meta+A" if sys.platform == "darwin" else "Control+A")
            page.keyboard.type(f"# {title_b}\n\nbody of B\n")
            time.sleep(1.5)

            # Edit doc A in the same tab.
            page.goto(f"{base_url}/doc/{doc_a}", wait_until="domcontentloaded")
            _wait_editor_contains(page, "Start typing")
            time.sleep(3)
            page.locator("#editor-pane .monaco-editor").first.click()
            page.keyboard.press("Meta+A" if sys.platform == "darwin" else "Control+A")
            page.keyboard.type(f"# Doc A {suffix}\n\n{marker_a}\n")
            time.sleep(1.5)

            # Back to My Documents, then open doc B from the list.
            page.get_by_role("link", name="My Documents").first.click()
            page.get_by_role("link", name=title_b).click()
            page.wait_for_url(f"**/doc/{doc_b}")
            _wait_editor_contains(page, "body of B")
            time.sleep(4)  # past the Yjs sync timeout + rebind

            value = _editor_value(page)
            page.screenshot(path=str(output_dir / "doc_b_after_switch.png"), full_page=True)
            if marker_a in value:
                print(f"FAIL: doc B editor contains doc A content:\n{value}")
                return 1

            # Persisted content of B must also be clean.
            page.goto(f"{base_url}/doc/{doc_b}", wait_until="domcontentloaded")
            _wait_editor_contains(page, "body of B")
            time.sleep(3)
            value = _editor_value(page)
            if marker_a in value:
                print(f"FAIL: persisted doc B contains doc A content:\n{value}")
                return 1

            print("PASS: doc B unaffected by doc A edits")
            return 0
        except Exception as exc:
            page.screenshot(path=str(output_dir / "failure.png"), full_page=True)
            print(f"FAIL: {exc}")
            return 1
        finally:
            context.close()
            browser.close()


if __name__ == "__main__":
    raise SystemExit(main())
