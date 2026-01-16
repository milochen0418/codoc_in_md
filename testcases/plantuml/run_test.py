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
    page.get_by_role("heading", name="Collaborative Doc").wait_for()
    page.locator('button[title="Split View"]').wait_for()
    page.locator("#editor-pane .monaco-editor").wait_for(state="visible")
    page.locator("#preview-pane").wait_for(state="visible")
    time.sleep(0.25)


def main() -> int:
    base_url = os.getenv("BASE_URL", "http://127.0.0.1:3000").rstrip("/")
    output_dir = Path(os.getenv("OUTPUT_DIR", "testcases/plantuml/output"))
    output_dir.mkdir(parents=True, exist_ok=True)

    headless = env_bool("HEADLESS", True)
    timeout_ms = int(os.getenv("PW_TIMEOUT_MS", "30000"))

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(viewport={"width": 1280, "height": 720})
        page = context.new_page()
        page.set_default_timeout(timeout_ms)

        try:
            page.goto(base_url + "/doc/plantuml", wait_until="domcontentloaded")
            _wait_for_app_ready(page)

            page.wait_for_function(
                """() => {
                    const root = document.getElementById('preview-pane');
                    if (!root) return false;
                    const text = root.textContent || '';
                    return text.includes('@startuml') &&
                        text.includes('Alice') &&
                        text.includes('Bob') &&
                        text.includes('Authentication Request');
                }"""
            )

            time.sleep(0.25)
            page.screenshot(path=str(output_dir / "plantuml.png"), full_page=True)
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
        print(f"plantuml failed: {exc}", file=sys.stderr)
        raise
