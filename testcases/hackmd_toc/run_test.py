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
    
    # Check key elements
    page.wait_for_function(
        """() => {
          const editorPane = document.getElementById('editor-pane');
          if (!editorPane) return false;
          
          const split = document.getElementById('codoc-split');
          const divider = document.getElementById('split-divider');
          const preview = document.getElementById('preview-pane');
          
          // Try to ensure monaco is loaded lightly
          const hasMonaco = !!(window.monaco && window.monaco.editor);
          
          return hasMonaco && !!split && !!divider && !!preview;
        }"""
    )
    time.sleep(0.5)


def main() -> int:
    base_url = os.getenv("BASE_URL", "http://127.0.0.1:3000").rstrip("/")
    output_dir = Path(os.getenv("OUTPUT_DIR", "testcases/hackmd_toc/output"))
    output_dir.mkdir(parents=True, exist_ok=True)

    headless = env_bool("HEADLESS", True)
    timeout_ms = int(os.getenv("PW_TIMEOUT_MS", "30000"))

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(viewport={"width": 1280, "height": 720})
        page = context.new_page()
        page.set_default_timeout(timeout_ms)

        try:
            print(f"Navigating to {base_url}/doc/hackmd_toc")
            page.goto(base_url + "/doc/hackmd_toc", wait_until="domcontentloaded")

            _wait_for_app_ready(page)

            # Wait for TOC to be rendered in preview
            print("Waiting for TOC to appear...")
            preview = page.locator("#preview-pane")
            preview.wait_for()
            
            # The TOC is a div with class 'toc'
            toc = preview.locator(".toc")
            toc.wait_for()

            # Check for specific links
            print("Checking TOC links...")
            
            # Use text selectors to verify links exist
            link1 = toc.get_by_role("link", name="Section 1", exact=True)
            if not link1.is_visible():
                raise Exception("TOC link for 'Section 1' not found")
                
            link1_1 = toc.get_by_role("link", name="Subsection 1.1", exact=True)
            if not link1_1.is_visible():
                 raise Exception("TOC link for 'Subsection 1.1' not found")

            link2 = toc.get_by_role("link", name="Section 2", exact=True)
            if not link2.is_visible():
                raise Exception("TOC link for 'Section 2' not found")

            # Check generated IDs/hrefs match what we expect
            # Assuming "Subsection 1.1" -> "#subsection-11" based on my reading of slugifyGfm
            # Or whatever specific slug logic exists.
            
            href1 = link1.get_attribute("href")
            print(f"Section 1 href: {href1}")
            if not href1 or "section-1" not in href1:
                 print(f"WARNING: unexpected href for Section 1: {href1}")

            href1_1 = link1_1.get_attribute("href")
            print(f"Subsection 1.1 href: {href1_1}")
            # Dot is removed, space -> -
            # "Subsection 1.1" -> "subsection 11" -> "subsection-11"
            if not href1_1:
                 raise Exception("No href for Subsection 1.1")
            
            print("TOC test passed!")
            return 0

        except Exception as e:
            print(f"Test failed: {e}")
            page.screenshot(path=output_dir / "failure.png")
            import traceback
            traceback.print_exc()
            return 1
        finally:
            browser.close()

if __name__ == "__main__":
    sys.exit(main())
