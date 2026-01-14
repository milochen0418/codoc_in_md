import os
import sys
import time
import json
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

    # Ensure split view is active so the preview exists.
    if not page.evaluate(
        """() => {
            return !!document.getElementById('preview-pane');
        }"""
    ):
        page.locator('button[title="Split View"]').click()

    page.locator("#editor-pane .monaco-editor").wait_for(state="visible")
    page.locator("#preview-pane").wait_for(state="visible")

    # Give layout/JS a moment to settle.
    time.sleep(0.25)


def main() -> int:
    base_url = os.getenv("BASE_URL", "http://127.0.0.1:3000").rstrip("/")
    output_dir = Path(os.getenv("OUTPUT_DIR", "testcases/mathjax/output"))
    output_dir.mkdir(parents=True, exist_ok=True)

    headless = env_bool("HEADLESS", True)
    # KaTeX rendering can be a bit slower on cold-start (compile + first render).
    timeout_ms = int(os.getenv("PW_TIMEOUT_MS", "60000"))

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(viewport={"width": 1280, "height": 720})
        page = context.new_page()
        page.set_default_timeout(timeout_ms)

        try:
            page.goto(base_url + "/", wait_until="domcontentloaded")
            _wait_for_app_ready(page)

            page.goto(base_url + "/doc/mathjax", wait_until="domcontentloaded")
            page.locator("#preview-pane").wait_for(state="visible")

            # Wait for preview to have some content.
            page.wait_for_function(
                """() => {
                    const root = document.getElementById('preview-pane');
                    if (!root) return false;
                    const t = (root.innerText || '').trim();
                    return t.length > 20;
                }"""
            )

            # Wait for KaTeX DOM to appear (polling so we can log useful diagnostics).
            start = time.time()
            last_stats: dict | None = None
            while True:
                last_stats = page.evaluate(
                    """() => {
                        const root = document.getElementById('preview-pane');
                        if (!root) return { ok: false, reason: 'no-root' };

                        const katexInline = root.querySelectorAll('.katex');
                        const katexDisplay = root.querySelectorAll('.katex-display');
                        const errs = root.querySelectorAll('.katex-error');

                        let badDollarOutsideCode = false;
                        const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
                        let node;
                        while ((node = walker.nextNode())) {
                            const v = String(node.nodeValue || '');
                            if (!v.includes('$$')) continue;
                            const el = node.parentElement;
                            if (!el) { badDollarOutsideCode = true; break; }
                            if (el.closest('code,pre')) continue;
                            badDollarOutsideCode = true;
                            break;
                        }

                        const inlineText = Array.from(katexInline).slice(0, 8).map((n) => String(n.textContent || '')).join(' ');
                        const displayText = Array.from(katexDisplay).slice(0, 4).map((n) => String(n.textContent || '')).join(' ');

                        const hasEinstein = /E\s*=\s*m\s*c/.test(inlineText.replace(/\s+/g, ' '));
                        const hasGamma = displayText.includes('Γ') || displayText.toLowerCase().includes('gamma');
                        const hasIntegral = displayText.includes('∫') || displayText.includes('∞') || displayText.includes('pi') || displayText.includes('π');

                        const ok = (katexInline.length >= 2) && (katexDisplay.length >= 1) && (errs.length === 0) && (!badDollarOutsideCode) && hasEinstein;
                        return {
                            ok,
                            katexInline: katexInline.length,
                            katexDisplay: katexDisplay.length,
                            katexError: errs.length,
                            badDollarOutsideCode,
                            hasEinstein,
                            hasGamma,
                            hasIntegral,
                        };
                    }"""
                )

                if last_stats and last_stats.get("ok"):
                    break
                if time.time() - start > (timeout_ms / 1000.0):
                    raise TimeoutError(f"KaTeX not ready; stats={last_stats}")
                time.sleep(0.5)

            # The page is long; validate math rendering in the later delimiter section too.
            page.wait_for_function(
                """() => {
                    const root = document.getElementById('preview-pane');
                    if (!root) return false;
                    const text = (root.innerText || '');
                    return text.includes('另一種定界符');
                }"""
            )
            bottom_math_ok = page.evaluate(
                """() => {
                    const root = document.getElementById('preview-pane');
                    if (!root) return { ok: false, reason: 'no-root' };

                    const inline = Array.from(root.querySelectorAll('.katex'))
                        .map((n) => String(n.textContent || ''))
                        .join(' ')
                        .replace(/\s+/g, '');
                    const display = Array.from(root.querySelectorAll('.katex-display'))
                        .map((n) => String(n.textContent || ''))
                        .join(' ')
                        .replace(/\s+/g, '');

                    // Expect the MathJax-style delimiters section to be rendered.
                    const hasPythagorean = inline.includes('a2+b2=c2');
                    const hasNormExample = display.includes('x1') && display.includes('x2');
                    return { ok: hasPythagorean && hasNormExample, hasPythagorean, hasNormExample };
                }"""
            )
            if not bottom_math_ok.get("ok"):
                raise AssertionError(f"Bottom-of-page math not rendered: {bottom_math_ok}")

            # Abbreviation should apply in normal text but not inside math.
            page.wait_for_function(
                """() => {
                    const root = document.getElementById('preview-pane');
                    if (!root) return false;
                    const abbr = root.querySelector('abbr[title="Application Programming Interface"]');
                    if (!abbr) return false;
                    // Ensure we didn't inject abbr tags inside KaTeX markup.
                    const anyAbbrInsideKatex = !!root.querySelector('.katex abbr');
                    return !anyAbbrInsideKatex;
                }"""
            )

            # Ensure MathJax-style delimiters in the doc are not leaking as plain text.
            offenders = page.evaluate(
                """() => {
                    const root = document.getElementById('preview-pane');
                    if (!root) return [{ needle: 'no-root', text: '' }];

                    const badNeedles = ['\\\\left\\\\lVert', '\\\\(', '\\\\['];
                    const out = [];
                    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
                    let node;
                    while ((node = walker.nextNode())) {
                        const v = String(node.nodeValue || '');
                        if (!v) continue;
                        const el = node.parentElement;
                        if (el && el.closest('code,pre')) continue;
                        // KaTeX keeps original TeX source in hidden MathML annotations.
                        if (el && el.closest('.katex-mathml,annotation')) continue;
                        for (const needle of badNeedles) {
                            if (v.includes(needle)) {
                                out.push({
                                    needle,
                                    text: v.slice(0, 200),
                                    tag: el ? (el.tagName || '') : '',
                                });
                            }
                        }
                        if (out.length >= 5) break;
                    }
                    return out;
                }"""
            )
            if offenders:
                raise AssertionError(f"MathJax delimiters leaked as text: {offenders}")

            time.sleep(0.25)
            page.screenshot(path=str(output_dir / "mathjax.png"), full_page=True)
            return 0
        except Exception:
            try:
                try:
                    # Capture some diagnostics for debugging.
                    stats = page.evaluate(
                        """() => {
                            const root = document.getElementById('preview-pane');
                            if (!root) return { ok: false, reason: 'no-root' };

                            const errEls = Array.from(root.querySelectorAll('.katex-error')).slice(0, 5);
                            const katexErrorTexts = errEls.map((el) => String(el.textContent || '').slice(0, 200));

                            const badDollarNodes = [];
                            const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
                            let node;
                            while ((node = walker.nextNode())) {
                                const v = String(node.nodeValue || '');
                                if (!v.includes('$$')) continue;
                                const el = node.parentElement;
                                const tag = el ? (el.tagName || '') : '';
                                const inCode = el ? !!el.closest('code,pre') : false;
                                if (inCode) continue;
                                badDollarNodes.push({
                                    text: v.slice(0, 200),
                                    tag,
                                });
                                if (badDollarNodes.length >= 5) break;
                            }

                            return {
                                katex: root.querySelectorAll('.katex').length,
                                katexDisplay: root.querySelectorAll('.katex-display').length,
                                katexError: root.querySelectorAll('.katex-error').length,
                                katexErrorTexts,
                                badDollarNodes,
                                previewTextHead: String((root.innerText || '').slice(0, 500)),
                            };
                        }"""
                    )
                    (output_dir / "debug.json").write_text(
                        json.dumps(stats, ensure_ascii=False, indent=2),
                        encoding="utf-8",
                    )
                except Exception:
                    pass
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
        print(f"mathjax failed: {exc}", file=sys.stderr)
        raise
