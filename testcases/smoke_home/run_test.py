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


def _wait_for_app_ready(page, *, require_preview_tables: bool = False) -> None:
    # The app may redirect; wait for stable UI.
    page.get_by_role("heading", name="Collaborative Doc").wait_for()
    page.locator('button[title="Split View"]').wait_for()
    page.get_by_role("button", name="New Document").wait_for()

    # Ensure split view is active so the divider/preview exist.
    # Only click if split layout isn't already present (avoid toggling behaviors).
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
          const split = document.getElementById('codoc-split');
          const divider = document.getElementById('split-divider');
          const preview = document.getElementById('preview-pane');
          return hasScrollable && monacoReady && !!split && !!divider && !!preview;
        }"""
    )

    if require_preview_tables:
        page.wait_for_function(
            """() => {
                const root = document.getElementById('preview-pane');
                if (!root) return false;
                return (root.querySelectorAll('table') || []).length > 0;
            }"""
        )

    # Give layout/JS a moment to settle.
    time.sleep(0.25)


def main() -> int:
    base_url = os.getenv("BASE_URL", "http://127.0.0.1:3000").rstrip("/")
    output_dir = Path(os.getenv("OUTPUT_DIR", "testcases/smoke_home/output"))
    output_dir.mkdir(parents=True, exist_ok=True)

    headless = env_bool("HEADLESS", True)
    timeout_ms = int(os.getenv("PW_TIMEOUT_MS", "30000"))

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(viewport={"width": 1280, "height": 720})
        page = context.new_page()
        page.set_default_timeout(timeout_ms)

        try:
            page.goto(base_url + "/", wait_until="domcontentloaded")

            _wait_for_app_ready(page, require_preview_tables=False)

            # Also validate the emojify fixture doc renders (no network dependency; just DOM).
            page.goto(base_url + "/doc/emojify", wait_until="domcontentloaded")
            page.locator("#preview-pane").wait_for(state="visible")
            page.wait_for_function(
                """() => {
                    const root = document.getElementById('preview-pane');
                    if (!root) return false;
                    return (root.querySelectorAll('img.emoji') || []).length > 0;
                }"""
            )

            # Validate HackMD-style image syntax:
            # - reference-style image: ![Alt text][id] + [id]: ...
            # - size suffix: ![Minion](... =200x200)
            page.goto(base_url + "/doc/images", wait_until="domcontentloaded")
            page.locator("#preview-pane").wait_for(state="visible")
            page.wait_for_function(
                """() => {
                    const root = document.getElementById('preview-pane');
                    if (!root) return false;

                    const imgs = Array.from(root.querySelectorAll('img'));
                    if (imgs.length < 3) return false;

                    const hasRef = imgs.some((img) => (img.getAttribute('src') || '').includes('dojocat.jpg'));
                    if (!hasRef) return false;

                    const sized = imgs.find((img) => (img.getAttribute('src') || '').includes('minion.png') && (img.getAttribute('width') === '200' || img.getAttribute('height') === '200' || (img.getAttribute('style') || '').includes('200px')));
                    if (!sized) return false;

                    const w = parseInt(sized.getAttribute('width') || '0', 10);
                    const h = parseInt(sized.getAttribute('height') || '0', 10);
                    return (w === 200 && h === 200) || ((sized.getAttribute('style') || '').includes('width:200px') && (sized.getAttribute('style') || '').includes('height:200px'));
                }"""
            )

            # Give layout a moment to settle for screenshots.
            time.sleep(0.25)

            page.screenshot(path=str(output_dir / "smoke.png"), full_page=True)
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
        print(f"smoke_home failed: {exc}", file=sys.stderr)
        raise
