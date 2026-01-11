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

    # Ensure split view is active so the divider/preview exist.
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

    # Give layout/JS a moment to settle.
    time.sleep(0.25)


def _set_test_markdown(page) -> None:
    # Deterministic content so heading-based sync is testable.
    def para_lines(prefix: str, count: int) -> str:
        return "\n\n".join([f"{prefix} paragraph {i}: lorem ipsum dolor sit amet." for i in range(count)])

    md = "\n".join(
        [
            "# Split View Operate Test",
            "",
            "Intro paragraph.",
            "",
            "## Alpha",
            "",
            para_lines("Alpha", 40),
            "",
            "## Beta",
            "",
            para_lines("Beta", 80),
            "",
            "## Gamma",
            "",
            para_lines("Gamma", 80),
            "",
        ]
    )

    page.evaluate(
        """(md) => {
          const editors = window.monaco?.editor?.getEditors?.() || [];
          const ed = editors[0];
          if (!ed) throw new Error('Monaco editor not ready');
          ed.setValue(md);
        }""",
        md,
    )

    # Wait for preview to reflect new content.
    page.wait_for_function(
        """() => {
          const preview = document.getElementById('preview-pane');
          if (!preview) return false;
          const text = preview.innerText || '';
          return text.includes('Split View Operate Test') && text.includes('Alpha') && text.includes('Beta') && text.includes('Gamma');
        }"""
    )
    time.sleep(0.2)


def _get_split_left_pct(page) -> float:
    return float(
        page.evaluate(
            """() => {
              const el = document.getElementById('codoc-split');
              if (!el) return NaN;
              const raw = el.style.getPropertyValue('--codoc-split-left') || '';
              const m = /([0-9.]+)/.exec(raw);
              if (m) return parseFloat(m[1]);
              // Default is 50% when unset.
              return 50;
            }"""
        )
    )


def _get_locked(page) -> bool:
    return bool(
        page.evaluate(
            """() => {
              const el = document.getElementById('codoc-split');
              if (!el) return false;
              const viaDataset = el.dataset ? el.dataset.locked : null;
              const viaAttr = el.getAttribute('data-locked') || el.getAttribute('data_locked');
              const raw = viaDataset != null ? viaDataset : viaAttr;
              return raw === true || raw === 'true';
            }"""
        )
    )


def _get_preview_scroll_top(page) -> float:
    return float(
        page.evaluate(
            """() => {
              const el = document.getElementById('preview-pane');
              if (!el) return 0;
              return el.scrollTop || 0;
            }"""
        )
    )


def _get_editor_scroll_top(page) -> float:
    return float(
        page.evaluate(
            """() => {
              const ed = (window.monaco?.editor?.getEditors?.() || [])[0];
              if (!ed || typeof ed.getScrollTop !== 'function') return 0;
              return ed.getScrollTop();
            }"""
        )
    )


def _scroll_editor_to_heading(page, heading_text: str) -> None:
    page.evaluate(
        """(headingText) => {
          const ed = (window.monaco?.editor?.getEditors?.() || [])[0];
          if (!ed) throw new Error('Monaco editor not ready');
          const model = ed.getModel();
          if (!model) throw new Error('Monaco model not ready');
          const wanted = `## ${headingText}`;
          const lineCount = model.getLineCount();
          let headingLine = null;
          for (let i = 1; i <= lineCount; i += 1) {
            if ((model.getLineContent(i) || '').trim() === wanted) {
              headingLine = i;
              break;
            }
          }
          if (!headingLine) throw new Error(`Heading not found: ${wanted}`);
          // Put a line a bit below the heading near the top of the viewport.
          const target = Math.min(lineCount, headingLine + 4);
                    // Force an actual scroll so onDidScrollChange fires (needed for sync).
                    if (typeof ed.getTopForLineNumber === 'function' && typeof ed.setScrollTop === 'function') {
                        const topPx = ed.getTopForLineNumber(target);
                        ed.setScrollTop(topPx);
                    }
                    if (typeof ed.revealLineNearTop === 'function') {
                        ed.revealLineNearTop(target);
                    } else if (typeof ed.revealLineInCenter === 'function') {
                        ed.revealLineInCenter(target);
                    }
        }""",
        heading_text,
    )


def _assert_preview_heading_near_top(page, heading_text: str) -> None:
    ok = page.evaluate(
        """(headingText) => {
          const preview = document.getElementById('preview-pane');
          if (!preview) return false;
          const pr = preview.getBoundingClientRect();
          const headings = Array.from(preview.querySelectorAll('h1,h2,h3,h4,h5,h6'));
          const target = headings.find((h) => (h.textContent || '').trim() === headingText);
          if (!target) return false;
          const r = target.getBoundingClientRect();
          const delta = r.top - pr.top;
          // JS sync places the heading close to the top (with a small padding offset).
                    return delta >= -80 && delta <= 160;
        }""",
        heading_text,
    )
    if not ok:
        raise AssertionError(f"Preview heading not near top: {heading_text}")


def main() -> int:
    base_url = os.getenv("BASE_URL", "http://127.0.0.1:3000").rstrip("/")
    output_dir = Path(os.getenv("OUTPUT_DIR", "testcases/split_view_operate/output"))
    output_dir.mkdir(parents=True, exist_ok=True)

    headless = env_bool("HEADLESS", True)
    timeout_ms = int(os.getenv("PW_TIMEOUT_MS", "30000"))
    slowmo_ms = int(os.getenv("PW_SLOWMO_MS", "0"))

    with sync_playwright() as p:
        launch_kwargs = {"headless": headless}
        if slowmo_ms > 0:
            launch_kwargs["slow_mo"] = slowmo_ms
        browser = p.chromium.launch(**launch_kwargs)
        context = browser.new_context(viewport={"width": 1280, "height": 720})
        page = context.new_page()
        page.set_default_timeout(timeout_ms)

        try:
            # Requirement: use /doc/embeds as the entry point.
            page.goto(base_url + "/doc/embeds", wait_until="domcontentloaded")
            _wait_for_app_ready(page)

            _set_test_markdown(page)

            # 1) Divider drag should resize editor/preview widths.
            before_pct = _get_split_left_pct(page)

            container_box = page.locator("#codoc-split").bounding_box()
            divider_box = page.locator("#split-divider").bounding_box()
            if not container_box or not divider_box:
                raise RuntimeError("Missing split layout elements")

            start_x = divider_box["x"] + divider_box["width"] / 2
            start_y = divider_box["y"] + 3  # avoid the lock button (center)
            target_x = container_box["x"] + container_box["width"] * 0.7
            target_y = start_y

            page.mouse.move(start_x, start_y)
            page.mouse.down()
            page.mouse.move(target_x, target_y)
            page.mouse.up()

            time.sleep(0.2)
            after_pct = _get_split_left_pct(page)
            if abs(after_pct - before_pct) < 5:
                raise AssertionError(f"Split drag did not change width enough: {before_pct} -> {after_pct}")

            # 2) Lock button toggles locked/unlocked.
            lock_btn = page.locator("#split-divider button")
            lock_btn.wait_for(state="visible")

            # Ensure we can see both states.
            if not _get_locked(page):
                lock_btn.click()
                page.wait_for_function("() => (document.getElementById('codoc-split')?.getAttribute('data-locked') || document.getElementById('codoc-split')?.getAttribute('data_locked') || '').toString() === 'true'")

            lock_btn.click()  # unlock
            page.wait_for_function(
                """() => {
                  const el = document.getElementById('codoc-split');
                  if (!el) return false;
                  const viaDataset = el.dataset ? el.dataset.locked : null;
                  const viaAttr = el.getAttribute('data-locked') || el.getAttribute('data_locked');
                  const raw = viaDataset != null ? viaDataset : viaAttr;
                  return !(raw === true || raw === 'true');
                }"""
            )
            if _get_locked(page):
                raise AssertionError("Expected unlocked state")

            # 3) Unlocked: preview/editor scroll independently.
            # Scroll preview with mouse wheel.
            preview_box = page.locator("#preview-pane").bounding_box()
            editor_box = page.locator("#editor-pane").bounding_box()
            if not preview_box or not editor_box:
                raise RuntimeError("Missing preview/editor panes")

            page.mouse.move(preview_box["x"] + preview_box["width"] / 2, preview_box["y"] + 20)
            p_before = _get_preview_scroll_top(page)
            page.mouse.wheel(0, 900)
            time.sleep(0.2)
            p_after = _get_preview_scroll_top(page)
            if p_after <= p_before + 5:
                raise AssertionError("Preview did not scroll in unlocked mode")

            # Now scroll editor with mouse wheel; preview should not auto-follow.
            page.mouse.move(editor_box["x"] + editor_box["width"] / 2, editor_box["y"] + 20)
            p_before_editor_scroll = _get_preview_scroll_top(page)
            e_before = _get_editor_scroll_top(page)
            page.mouse.wheel(0, 900)
            time.sleep(0.3)
            e_after = _get_editor_scroll_top(page)
            p_after_editor_scroll = _get_preview_scroll_top(page)

            if e_after <= e_before + 5:
                raise AssertionError("Editor did not scroll in unlocked mode")
            if abs(p_after_editor_scroll - p_before_editor_scroll) > 8:
                raise AssertionError("Preview unexpectedly synced while unlocked")

            # 4) Locked: preview should sync to the editor's top visible heading.
            lock_btn.click()  # lock
            page.wait_for_function(
                """() => {
                  const el = document.getElementById('codoc-split');
                  if (!el) return false;
                  const viaDataset = el.dataset ? el.dataset.locked : null;
                  const viaAttr = el.getAttribute('data-locked') || el.getAttribute('data_locked');
                  const raw = viaDataset != null ? viaDataset : viaAttr;
                  return raw === true || raw === 'true';
                }"""
            )

            # Reset preview scroll a bit to make the sync effect obvious.
            page.evaluate("() => { const p = document.getElementById('preview-pane'); if (p) p.scrollTop = 0; }")
            time.sleep(0.1)

            _scroll_editor_to_heading(page, "Beta")

            # Wait until the preview heading is near the top (sync is requestAnimationFrame-based).
            page.wait_for_function(
                """() => {
                  const preview = document.getElementById('preview-pane');
                  if (!preview) return false;
                  const pr = preview.getBoundingClientRect();
                  const headings = Array.from(preview.querySelectorAll('h1,h2,h3,h4,h5,h6'));
                  const target = headings.find((h) => (h.textContent || '').trim() === 'Beta');
                  if (!target) return false;
                  const r = target.getBoundingClientRect();
                  const delta = r.top - pr.top;
                                    return delta >= -80 && delta <= 160;
                }"""
            )
            _assert_preview_heading_near_top(page, "Beta")

            page.screenshot(path=str(output_dir / "split_view_operate.png"), full_page=True)
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
        print(f"split_view_operate failed: {exc}", file=sys.stderr)
        raise
