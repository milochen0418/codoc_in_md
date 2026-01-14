import os
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright


def env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def _wait_for_app_ready(page) -> None:
    # The app may redirect; wait for stable UI.
    page.get_by_role("heading", name="Collaborative Doc").wait_for()
    page.locator('button[title="Split View"]').wait_for()

    # Ensure split view is active so the preview exists.
    if not page.evaluate(
        """() => {
            return !!document.getElementById('codoc-split') &&
                   !!document.getElementById('split-divider') &&
                   !!document.getElementById('preview-pane');
        }"""
    ):
        page.locator('button[title="Split View"]').click()

    # Monaco can mount after the header is visible; wait for it to be usable.
    page.locator("#editor-pane .monaco-editor").wait_for(state="visible")
    page.wait_for_function(
        """() => {
          const editorPane = document.getElementById('editor-pane');
          if (!editorPane) return false;
          const hasScrollable = !!editorPane.querySelector('.monaco-editor .monaco-scrollable-element');
          const monacoReady = !!(
            window.monaco &&
            window.monaco.editor &&
            typeof window.monaco.editor.getEditors === 'function' &&
            (window.monaco.editor.getEditors() || []).length
          );
          const preview = document.getElementById('preview-pane');
          return hasScrollable && monacoReady && !!preview;
        }"""
    )

    # Give layout/JS a moment to settle.
    time.sleep(0.25)


def main() -> int:
    base_url = os.getenv("BASE_URL", "http://127.0.0.1:3000").rstrip("/")
    output_dir = Path(os.getenv("OUTPUT_DIR", "testcases/fontawesome_icons/output"))
    output_dir.mkdir(parents=True, exist_ok=True)

    headless = env_bool("HEADLESS", True)
    timeout_ms = int(os.getenv("PW_TIMEOUT_MS", "30000"))

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(viewport={"width": 1280, "height": 720})
        page = context.new_page()
        page.set_default_timeout(timeout_ms)

        try:
            page.goto(base_url + "/doc/fontawesome", wait_until="domcontentloaded")
            _wait_for_app_ready(page)

            # Assert at least one Font Awesome icon survives rendering.
            # We accept either:
            # - class was preserved/restored: <* class="fa ...">
            # - or class was stripped but data-codoc-fa-class preserved: <* data-codoc-fa-class="fa ...">
            page.wait_for_function(
                """() => {
                    const root = document.getElementById('preview-pane');
                    if (!root) return false;

                    const hasClassIcon = !!root.querySelector('.fa');
                    const hasDataIcon = !!root.querySelector('[data-codoc-fa-class], [data-fa-class]');
                    return hasClassIcon || hasDataIcon;
                }"""
            )

            # Stronger check: our client fix should restore class=fa.
            page.wait_for_function(
                """() => {
                    const root = document.getElementById('preview-pane');
                    if (!root) return false;
                    return !!root.querySelector('.fa');
                }"""
            )

            # Ensure a few specific icons from the fixture render.
            page.wait_for_function(
                """() => {
                    const root = document.getElementById('preview-pane');
                    if (!root) return false;
                    const mustHave = ['.fa-github', '.fa-camera', '.fa-cog', '.fa-check', '.fa-times'];
                    return mustHave.every((sel) => !!root.querySelector(sel));
                }"""
            )

            # Ensure fenced code blocks are not rewritten (we should see the literal <i ...> text in code).
            page.wait_for_function(
                """() => {
                    const root = document.getElementById('preview-pane');
                    if (!root) return false;
                    const pres = Array.from(root.querySelectorAll('pre'));
                    return pres.some((n) => (n.textContent || '').includes('<i class="fa fa-github"></i>'));
                }"""
            )

            page.screenshot(path=str(output_dir / "fontawesome_icons.png"), full_page=True)
            return 0
        except Exception:
            try:
                page.screenshot(path=str(output_dir / "failure.png"), full_page=True)
            except Exception:
                pass
            raise
        finally:
            context.close()
            browser.close()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise
    except Exception as exc:
        print(f"fontawesome_icons failed: {exc}", file=sys.stderr)
        raise
