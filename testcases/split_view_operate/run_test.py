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


def _scroll_preview_by(page, delta_y: int) -> None:
        page.evaluate(
                """(dy) => {
                    const p = document.getElementById('preview-pane');
                    if (!p) throw new Error('Preview not ready');
                    p.scrollTop = (p.scrollTop || 0) + dy;
                }""",
                delta_y,
        )


def _scroll_editor_by(page, delta_px: int) -> None:
        page.evaluate(
                """(dy) => {
                    const ed = (window.monaco?.editor?.getEditors?.() || [])[0];
                    if (!ed || typeof ed.getScrollTop !== 'function' || typeof ed.setScrollTop !== 'function') {
                        throw new Error('Monaco editor not ready');
                    }
                    ed.setScrollTop(ed.getScrollTop() + dy);
                }""",
                delta_px,
        )


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
                    // Bring the heading itself near the top so split-sync resolves to this heading.
                    const target = headingLine;
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


def _get_editor_top_heading_text(page) -> str | None:
        return page.evaluate(
                """() => {
                    const ed = (window.monaco?.editor?.getEditors?.() || [])[0];
                    if (!ed) return null;
                    const model = typeof ed.getModel === 'function' ? ed.getModel() : null;
                    if (!model || typeof model.getLineCount !== 'function') return null;

                    let topLine = 1;
                    if (typeof ed.getVisibleRanges === 'function') {
                        const ranges = ed.getVisibleRanges() || [];
                        if (ranges.length && ranges[0] && ranges[0].startLineNumber) {
                            topLine = ranges[0].startLineNumber;
                        }
                    }

                    const maxLookback = 400;
                    const minLine = Math.max(1, topLine - maxLookback);
                    for (let ln = topLine; ln >= minLine; ln -= 1) {
                        const line = model.getLineContent(ln) || '';
                        const m = /^(#{1,6})\s+(.+?)\s*$/.exec(line);
                        if (m) return String(m[2] || '').trim();
                    }
                    return null;
                }"""
        )


def _get_preview_top_visible_heading_text(page) -> str | None:
        return page.evaluate(
                """() => {
                    const preview = document.getElementById('preview-pane');
                    if (!preview) return null;
                    const pr = preview.getBoundingClientRect();
                    const headings = Array.from(preview.querySelectorAll('h1,h2,h3,h4,h5,h6'));
                    const visible = headings
                        .map((h) => ({ h, r: h.getBoundingClientRect() }))
                        .filter((x) => x.r.bottom > pr.top + 5 && x.r.top < pr.bottom - 5)
                        .map((x) => ({ text: (x.h.textContent || '').trim(), topDelta: x.r.top - pr.top }))
                        .filter((x) => x.text);
                    if (!visible.length) return null;
                    visible.sort((a, b) => a.topDelta - b.topDelta);
                    return visible[0].text;
                }"""
        )


def _dump_debug(page, output_dir: Path, name: str) -> None:
        try:
                payload = page.evaluate(
                        """() => {
                            const split = document.getElementById('codoc-split');
                            const preview = document.getElementById('preview-pane');
                            const viaDataset = split?.dataset ? split.dataset.locked : null;
                            const viaAttr = split?.getAttribute('data-locked') || split?.getAttribute('data_locked');
                            const rawLocked = viaDataset != null ? viaDataset : viaAttr;
                            const locked = rawLocked === true || rawLocked === 'true';

                            const ed = (window.monaco?.editor?.getEditors?.() || [])[0];
                            const editorScrollTop = ed?.getScrollTop?.() ?? null;
                            const editorVisibleRanges = ed?.getVisibleRanges?.() ?? null;

                            function editorTopHeadingText() {
                                try {
                                    const model = ed && typeof ed.getModel === 'function' ? ed.getModel() : null;
                                    if (!model || typeof model.getLineCount !== 'function') return null;

                                    let topLine = 1;
                                    if (ed && typeof ed.getVisibleRanges === 'function') {
                                        const ranges = ed.getVisibleRanges() || [];
                                        if (ranges.length && ranges[0] && ranges[0].startLineNumber) {
                                            topLine = ranges[0].startLineNumber;
                                        }
                                    }

                                    const maxLookback = 400;
                                    const minLine = Math.max(1, topLine - maxLookback);
                                    for (let ln = topLine; ln >= minLine; ln -= 1) {
                                        const line = model.getLineContent(ln) || '';
                                        const m = /^(#{1,6})\s+(.+?)\s*$/.exec(line);
                                        if (m) return String(m[2] || '').trim();
                                    }
                                    return null;
                                } catch (_) {
                                    return null;
                                }
                            }

                            function previewTopVisibleHeadingText() {
                                try {
                                    if (!preview) return null;
                                    const pr = preview.getBoundingClientRect();
                                    const headings = Array.from(preview.querySelectorAll('h1,h2,h3,h4,h5,h6'));
                                    const visible = headings
                                        .map((h) => ({ h, r: h.getBoundingClientRect() }))
                                        .filter((x) => x.r.bottom > pr.top + 5 && x.r.top < pr.bottom - 5)
                                        .map((x) => ({ text: (x.h.textContent || '').trim(), topDelta: x.r.top - pr.top }))
                                        .filter((x) => x.text);
                                    if (!visible.length) return null;
                                    visible.sort((a, b) => a.topDelta - b.topDelta);
                                    return visible[0].text;
                                } catch (_) {
                                    return null;
                                }
                            }

                            const pr = preview?.getBoundingClientRect?.() ?? null;
                            const headings = preview
                                ? Array.from(preview.querySelectorAll('h1,h2,h3,h4,h5,h6')).slice(0, 20).map((h) => {
                                        const r = h.getBoundingClientRect();
                                        return { text: (h.textContent || '').trim(), topDelta: pr ? (r.top - pr.top) : null };
                                    })
                                : [];

                            return {
                                url: window.location.href,
                                locked,
                                splitLeft: split?.style?.getPropertyValue('--codoc-split-left') || null,
                                previewScrollTop: preview?.scrollTop ?? null,
                                editorScrollTop,
                                editorVisibleRanges,
                                editorTopHeadingText: editorTopHeadingText(),
                                previewTopHeadingText: previewTopVisibleHeadingText(),
                                previewFirst20Headings: headings,
                            };
                        }"""
                )
                (output_dir / f"debug_{name}.json").write_text(
                        __import__("json").dumps(payload, ensure_ascii=False, indent=2),
                        encoding="utf-8",
                )
        except Exception:
                pass


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
            _wait_for_app_ready(page, require_preview_tables=True)

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
            # Scroll preview and editor independently.
            preview_box = page.locator("#preview-pane").bounding_box()
            editor_box = page.locator("#editor-pane").bounding_box()
            if not preview_box or not editor_box:
                raise RuntimeError("Missing preview/editor panes")

            p_before = _get_preview_scroll_top(page)
            _scroll_preview_by(page, 900)
            time.sleep(0.2)
            p_after = _get_preview_scroll_top(page)
            if p_after <= p_before + 5:
                raise AssertionError("Preview did not scroll in unlocked mode")

            # Now scroll editor; preview should not auto-follow.
            p_before_editor_scroll = _get_preview_scroll_top(page)
            e_before = _get_editor_scroll_top(page)
            _scroll_editor_by(page, 900)
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

            # Use an existing ATX heading in assets/hackmd_embeds.md to force a meaningful scroll.
            # The sync logic aligns to the editor's *top visible heading* (as detected by codoc_split.js),
            # so we compute that expected heading after the scroll.
            _scroll_editor_to_heading(page, "上傳圖片")

            expected_heading = _get_editor_top_heading_text(page)
            if not expected_heading:
                _dump_debug(page, output_dir, "locked_sync_no_editor_heading")
                raise AssertionError("Could not detect editor top heading after scrolling")
            try:
                page.wait_for_function(
                    """(expected) => {
                      const preview = document.getElementById('preview-pane');
                      if (!preview) return false;
                      const pr = preview.getBoundingClientRect();
                      const headings = Array.from(preview.querySelectorAll('h1,h2,h3,h4,h5,h6'));
                      const visible = headings
                        .map((h) => ({ h, r: h.getBoundingClientRect() }))
                        .filter((x) => x.r.bottom > pr.top + 5 && x.r.top < pr.bottom - 5)
                        .map((x) => ({ text: (x.h.textContent || '').trim(), topDelta: x.r.top - pr.top }))
                        .filter((x) => x.text);
                      if (!visible.length) return false;
                      visible.sort((a, b) => a.topDelta - b.topDelta);
                      const topText = visible[0].text;
                      return topText === expected;
                    }""",
                                        arg=expected_heading,
                    timeout=max(timeout_ms, 60000),
                )
            except Exception:
                _dump_debug(page, output_dir, "locked_sync_timeout")
                raise

            # Stronger check: the preview should now have the expected heading at the top.
            preview_top = _get_preview_top_visible_heading_text(page)
            if preview_top != expected_heading:
                _dump_debug(page, output_dir, "locked_sync_mismatch")
                raise AssertionError(
                    f"Locked sync mismatch: preview_top={preview_top!r}, expected={expected_heading!r}"
                )

            page.screenshot(path=str(output_dir / "split_view_operate.png"), full_page=True)
            return 0
        except Exception:
            try:
                page.screenshot(path=str(output_dir / "failure.png"), full_page=True)
                _dump_debug(page, output_dir, "failure")
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
