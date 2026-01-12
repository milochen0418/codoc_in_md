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

            # The app may redirect from `/` to a doc url; wait for stable UI.
            page.get_by_role("heading", name="Collaborative Doc").wait_for()
            page.locator('button[title="Split View"]').wait_for()
            page.get_by_role("button", name="New Document").wait_for()

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
                  return hasScrollable && monacoReady;
                }"""
            )

            # Preview should also be mounted.
            page.locator("#preview-pane").wait_for(state="visible")

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
