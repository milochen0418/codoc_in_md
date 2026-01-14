from __future__ import annotations

"""Generate a *complete* Font Awesome 4.7 fixture section for this project.

## What this script is for

This repo emulates HackMD/CodiMD Markdown rendering. One common HackMD pattern is
Font Awesome 4 HTML icons like:

        <i class="fa fa-github"></i>

In this project:

- The backend preprocessor `apply_hackmd_fontawesome_icons` rewrites/annotates
    these tags so the icon class list survives markdown sanitization.
- The frontend script `assets/fontawesome_fix.js` restores the `.fa ...` class
    from the preserved `data-codoc-fa-class` attribute.
- The E2E suite `testcases/fontawesome_icons/run_test.py` validates that icons
    actually render in the preview.

`assets/hackmd_fontawesome.md` is the fixture doc loaded by `/doc/fontawesome`.
We want it to contain *all* FA 4.7 icons so we can:

- Detect regressions where only some icon patterns survive.
- Catch sanitizer/preprocessor edge cases early.
- Provide a convenient manual visual reference page.

Maintaining the full list by hand is error-prone, so this script fetches the
official FA 4.7 CSS from the same CDN URL the app loads and extracts all
`.fa-<name>:before` selectors to build the fixture content.

## When to run it

- After changing anything related to Font Awesome rendering:
    - `apply_hackmd_fontawesome_icons` (backend transform)
    - `assets/fontawesome_fix.js` (client restore logic)
    - markdown sanitization / rendering pipeline changes
- When you want to refresh the full icon list (e.g., if the CDN content changes)
- If you edited `assets/hackmd_fontawesome.md` and want to re-insert the generated
    section cleanly.

## How to run it

This repo is Poetry-managed and targets Python 3.11.

        poetry env use python3.11
        poetry run python scripts/generate_fa47_fixture.py

The script is idempotent: it updates the section between the markers:

        <!-- BEGIN: FA47_ALL_ICONS -->
        ...generated content...
        <!-- END: FA47_ALL_ICONS -->

and leaves the rest of the file unchanged.

## Notes / guardrails

- The generated section includes a *full gallery* of icons, but it is wrapped
    in `<details>` so the page doesn't eagerly render thousands of nodes by default.
- We fetch the CSS with a User-Agent header to avoid occasional CDN bot blocking.
"""

import re
import urllib.request
from pathlib import Path

URL = "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.7.0/css/font-awesome.min.css"
MARKER_BEGIN = "<!-- BEGIN: FA47_ALL_ICONS -->"
MARKER_END = "<!-- END: FA47_ALL_ICONS -->"


def fetch_fa47_icons() -> list[str]:
    """Return all FA 4.7 icon names by scraping the CDN CSS.

    We parse `.fa-<name>:before { ... }` selectors from Font Awesome 4.7.
    The return values are *names without the `fa-` prefix* (e.g. `github`).

    Raises:
        RuntimeError: If the CSS fetch succeeds but no icons are parsed.
    """
    req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
    css = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
    icons = sorted(set(re.findall(r"\.fa-([a-z0-9-]+):before", css)))
    if not icons:
        raise RuntimeError("Failed to parse any .fa-*:before icons from FA 4.7 CSS")
    return icons


def build_section(icons: list[str]) -> str:
    """Build the Markdown section that gets inserted into the fixture.

    The section includes:
    - A `<details>` block containing a flex-wrapped gallery of rendered icons.
      We intentionally use `<i class="fa fa-..."></i>` so the backend + client
      restoration path is exercised.
    - Another `<details>` block listing all class names in plain text.
    - BEGIN/END markers so updates are idempotent.
    """
    gallery_items = []
    for name in icons:
        gallery_items.append(
            '<span style="display:inline-block;width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">'
            f'<i class="fa fa-{name}"></i> fa-{name}'
            "</span>"
        )

    return (
        "\n\n## 全部 Font Awesome 4.7 icons\n\n"
        f"來源（與 app 載入一致）：{URL}\n\n"
        f"總數：{len(icons)}\n\n"
        f"{MARKER_BEGIN}\n"
        "<details>\n"
        "<summary>展開：完整 icon gallery（全部渲染，較長）</summary>\n\n"
        "<div style=\"display:flex;flex-wrap:wrap;gap:10px;align-items:flex-start\">\n"
        + "\n".join(gallery_items)
        + "\n</div>\n"
        "</details>\n\n"
        "<details>\n"
        "<summary>展開：完整 class name 清單</summary>\n\n"
        "```text\n"
        + "\n".join([f"fa-{n}" for n in icons])
        + "\n```\n"
        "</details>\n"
        f"{MARKER_END}\n"
    )


def upsert_section(path: Path, section: str) -> None:
    """Insert or replace the generated section inside the fixture file.

    If markers exist, only the marked region is replaced. Otherwise, the section
    is appended to the end.
    """
    orig = path.read_text(encoding="utf-8")

    if MARKER_BEGIN in orig and MARKER_END in orig:
        pre = orig.split(MARKER_BEGIN, 1)[0].rstrip() + "\n\n"
        post = orig.split(MARKER_END, 1)[1].lstrip()
        updated = pre + section + "\n" + post
    else:
        updated = orig.rstrip() + "\n\n" + section

    path.write_text(updated, encoding="utf-8")


def main() -> None:
    """Entry point.

    Updates `assets/hackmd_fontawesome.md` in-place.
    """
    repo_root = Path(__file__).resolve().parents[1]
    md_path = repo_root / "assets" / "hackmd_fontawesome.md"

    icons = fetch_fa47_icons()
    section = build_section(icons)
    upsert_section(md_path, section)
    print(f"Updated {md_path} with {len(icons)} icons")


if __name__ == "__main__":
    main()
