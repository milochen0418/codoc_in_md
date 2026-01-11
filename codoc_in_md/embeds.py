"""HackMD-like embed directive processing.

This module provides a small, extensible architecture to translate directives like:
  {%youtube OPqDaOsYo-U %}
into raw HTML blocks suitable for rendering inside rx.markdown.

Add new embed types by registering an implementation in EMBED_EXTENSIONS.
"""

from __future__ import annotations

from dataclasses import dataclass
import base64
import binascii
import ipaddress
import html
import os
import re
from typing import Protocol
import json
import time
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse
from urllib.request import Request, urlopen

import reflex as rx
from starlette.requests import Request as StarletteRequest
from starlette.responses import HTMLResponse, Response


@dataclass(frozen=True, slots=True)
class EmbedDirective:
    name: str
    args: str
    raw: str


class EmbedExtension(Protocol):
    """An embed extension transforms a directive into an HTML block."""

    name: str

    def render(self, directive: EmbedDirective) -> str | None:
        """Return an HTML string if handled, otherwise None."""
        ...


@dataclass(frozen=True, slots=True)
class FencedCodeBlock:
    language: str
    code: str
    raw: str


class FencedBlockExtension(Protocol):
    """A fenced-block extension transforms a code block into an HTML block."""

    language: str

    def render(self, block: FencedCodeBlock) -> str | None:
        ...


_QUOTE_TAG_RE = re.compile(
    r"\[name=(?P<name>[^\]]+)\]\s*\[time=(?P<time>[^\]]+)\]\s*\[color=(?P<color>[^\]]+)\]"
)


@dataclass
class _QuoteNode:
    depth: int
    lines: list[str]
    children: list["_QuoteNode"]
    name: str | None = None
    time: str | None = None
    color: str | None = None


def _count_blockquote_depth(line: str) -> tuple[int, str] | None:
    """Return (depth, content) if line is a blockquote line, else None.

    Accepts `>` and `> ` and nesting like `>>` / `> >`.
    """

    i = 0
    n = len(line)
    depth = 0
    while i < n:
        # Optional leading spaces are allowed before a quote marker.
        while i < n and line[i] in " \t":
            i += 1
        if i < n and line[i] == ">":
            depth += 1
            i += 1
            # Optional single space after >
            if i < n and line[i] == " ":
                i += 1
            continue
        break

    if depth == 0:
        return None
    return depth, line[i:]


def _parse_quote_tree(lines: list[str]) -> list[_QuoteNode]:
    roots: list[_QuoteNode] = []
    stack: list[_QuoteNode] = []

    for raw in lines:
        parsed = _count_blockquote_depth(raw)
        if parsed is None:
            # Not a quote line (shouldn't happen here).
            continue
        depth, content = parsed

        while stack and stack[-1].depth > depth:
            stack.pop()

        if not stack or stack[-1].depth < depth:
            node = _QuoteNode(depth=depth, lines=[], children=[])
            if stack:
                stack[-1].children.append(node)
            else:
                roots.append(node)
            stack.append(node)

        # Now stack[-1].depth == depth
        stack[-1].lines.append(content.rstrip("\r\n"))

    return roots


def _extract_quote_meta(node: _QuoteNode) -> None:
    """Extract [name/time/color] tags from the node's lines.

    HackMD uses a separate line inside the quote to specify metadata.
    We remove that line from rendered content.
    """

    kept: list[str] = []
    for line in node.lines:
        m = _QUOTE_TAG_RE.search(line.strip())
        if m and node.name is None and node.time is None and node.color is None:
            node.name = m.group("name").strip()
            node.time = m.group("time").strip()
            node.color = m.group("color").strip()
            continue
        kept.append(line)
    node.lines = kept

    for child in node.children:
        _extract_quote_meta(child)


def _format_inline_md_minimal(text: str) -> str:
    """Minimal inline markdown rendering for quote bodies.

    Supports **bold** and `code`.
    """

    s = html.escape(text or "", quote=False)
    # Inline code first.
    s = re.sub(r"`([^`]+)`", lambda m: f"<code class=\"px-1 py-0.5 rounded bg-gray-100 text-gray-800\">{html.escape(m.group(1), quote=False)}</code>", s)
    # Bold.
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    return s


def _render_quote_node_html(node: _QuoteNode) -> str:
    color = (node.color or "#CBD5E1").strip()  # default similar to border-gray-300
    safe_color = _escape_attr(color)
    safe_name = html.escape(node.name or "", quote=False)
    safe_time = html.escape(node.time or "", quote=False)

    # Split into paragraphs by blank lines.
    paragraphs: list[str] = []
    buf: list[str] = []
    for line in node.lines:
        if not line.strip():
            if buf:
                paragraphs.append("\n".join(buf))
                buf = []
            continue
        buf.append(line)
    if buf:
        paragraphs.append("\n".join(buf))

    body_parts: list[str] = []
    for para in paragraphs:
        rendered = "<br/>".join(_format_inline_md_minimal(x) for x in para.split("\n"))
        body_parts.append(f"<p class=\"mb-3 last:mb-0 text-gray-700 leading-relaxed\">{rendered}</p>")

    for child in node.children:
        body_parts.append(_render_quote_node_html(child))

    user_icon = (
        "<svg viewBox=\"0 0 24 24\" aria-hidden=\"true\" "
        "style=\"width:1rem;height:1rem;color:#9CA3AF;flex:none\" "
        "fill=\"none\" stroke=\"currentColor\" "
        "stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\">"
        "<path d=\"M20 21a8 8 0 0 0-16 0\"/>"
        "<circle cx=\"12\" cy=\"8\" r=\"4\"/>"
        "</svg>"
    )
    clock_icon = (
        "<svg viewBox=\"0 0 24 24\" aria-hidden=\"true\" "
        "style=\"width:1rem;height:1rem;color:#9CA3AF;flex:none\" "
        "fill=\"none\" stroke=\"currentColor\" "
        "stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\">"
        "<circle cx=\"12\" cy=\"12\" r=\"9\"/>"
        "<path d=\"M12 7v6l3 2\"/>"
        "</svg>"
    )

    meta_html = ""
    if node.name or node.time:
        # HackMD-like meta row with user + clock icons.
        parts: list[str] = []
        if node.name:
            parts.append(
                "<span style=\"display:inline-flex;align-items:center;gap:0.25rem\">"
                + user_icon
                + f"<span style=\\\"font-weight:500;color:#374151\\\">{safe_name}</span>"
                + "</span>"
            )
        if node.time:
            parts.append(
                "<span style=\"display:inline-flex;align-items:center;gap:0.25rem\">"
                + clock_icon
                + f"<span>{safe_time}</span>"
                + "</span>"
            )
        meta_html = (
            "<div class=\"mt-2 text-sm text-gray-500\" "
            "style=\"display:flex;align-items:center;gap:0.75rem;flex-wrap:nowrap;white-space:nowrap;overflow-x:auto\">"
            "<span style=\"color:#9CA3AF\">—</span>"
            + "".join(parts)
            + "</div>"
        )

    # Use a dedicated wrapper so nested quotes look consistent.
    return (
        f"<div class=\"my-4 pl-4 border-l-4\" style=\"border-left-color:{safe_color}\">"
        + "".join(body_parts)
        + meta_html
        + "</div>"
    )


def apply_hackmd_blockquote_labels(markdown_text: str) -> str:
    """Render HackMD-style blockquote labels.

    Detects quote blocks that include a metadata line of the form:
      [name=...] [time=...] [color=...]
    and converts the whole blockquote region into styled HTML.

    Nested quotes are supported.
    """

    text = markdown_text or ""
    if not text:
        return text

    lines = text.splitlines(keepends=True)
    out: list[str] = []
    i = 0

    while i < len(lines):
        if _count_blockquote_depth(lines[i]) is None:
            out.append(lines[i])
            i += 1
            continue

        # Collect a contiguous quote block.
        start = i
        i += 1
        while i < len(lines) and _count_blockquote_depth(lines[i]) is not None:
            i += 1
        block_lines = lines[start:i]

        # Only transform if we see at least one tag line anywhere in the block.
        if not any(_QUOTE_TAG_RE.search((_count_blockquote_depth(l) or (0, ""))[1].strip()) for l in block_lines):
            out.extend(block_lines)
            continue

        roots = _parse_quote_tree(block_lines)
        for r in roots:
            _extract_quote_meta(r)

        html_blocks = "\n".join(_render_quote_node_html(r) for r in roots)

        # Ensure HTML is treated as a block.
        out.append("\n" + html_blocks + "\n")

    return "".join(out)


_DIRECTIVE_RE = re.compile(
    r"\{\%\s*(?P<name>[A-Za-z0-9_-]+)(?:\s+(?P<args>.*?))?\s*\%\}",
    re.IGNORECASE | re.DOTALL,
)

_FENCED_BLOCK_RE = re.compile(
    # Only match *exactly* triple-backtick fences.
    # This avoids breaking markdown that uses longer fences like ````` to show ``` literally.
    r"```(?!`)(?P<info>[^\n]*)\r?\n(?P<body>.*?)(?:\r?\n)```(?!`)",
    re.DOTALL,
)


def _escape_attr(value: str) -> str:
    """Escape a string for use in an HTML attribute."""

    # html.escape(..., quote=True) does not escape single quotes.
    return html.escape(value, quote=True).replace("'", "&#x27;")


def _extract_youtube_id(value: str) -> str | None:
    value = (value or "").strip()
    if not value:
        return None

    # Common ID format is 11 chars; accept a safe subset.
    if re.fullmatch(r"[A-Za-z0-9_-]{6,64}", value):
        return value

    try:
        parsed = urlparse(value)
    except Exception:
        return None

    host = (parsed.netloc or "").lower()
    path = parsed.path or ""

    # https://www.youtube.com/watch?v=VIDEO_ID
    if "youtube.com" in host:
        query = parse_qs(parsed.query or "")
        vid = (query.get("v") or [""])[0]
        if re.fullmatch(r"[A-Za-z0-9_-]{6,64}", vid):
            return vid
        # https://www.youtube.com/embed/VIDEO_ID
        if path.startswith("/embed/"):
            candidate = path.split("/embed/", 1)[1].split("/", 1)[0]
            if re.fullmatch(r"[A-Za-z0-9_-]{6,64}", candidate):
                return candidate

    # https://youtu.be/VIDEO_ID
    if host.endswith("youtu.be"):
        candidate = path.lstrip("/").split("/", 1)[0]
        if re.fullmatch(r"[A-Za-z0-9_-]{6,64}", candidate):
            return candidate

    return None


_OEMBED_CACHE: dict[str, tuple[float, str]] = {}
_OEMBED_TTL_S = 60 * 60 * 24


def _backend_base_url() -> str:
    """Base URL for the Reflex backend (used by embed iframes).

    Default matches Reflex dev backend port. Override via env for other deployments.
    """

    return os.getenv("CODOC_BACKEND_BASE_URL", "http://localhost:8000").rstrip("/")


def _encode_code_b64(code: str) -> str:
    """Encode text to URL-safe base64 without padding."""

    raw = (code or "").encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _smart_quotes(text: str) -> str:
    """Best-effort smart quotes (like HackMD/Remarkable typographer).

    Applies to plain text only (caller must exclude code spans/blocks).
    """

    out: list[str] = []
    n = len(text)

    def _prev_nonspace(i: int) -> str:
        j = i - 1
        while j >= 0 and text[j].isspace():
            j -= 1
        return text[j] if j >= 0 else ""

    def _next_nonspace(i: int) -> str:
        j = i + 1
        while j < n and text[j].isspace():
            j += 1
        return text[j] if j < n else ""

    for i, ch in enumerate(text):
        if ch == '"':
            prev = _prev_nonspace(i)
            nxt = _next_nonspace(i)
            is_open = (not prev) or prev in "([{" or prev in "\n\r\t" or prev == "-"
            # If followed by punctuation or end, treat as closing.
            if not nxt or nxt in ")]}.,:;!?":
                is_open = False
            out.append("\u201c" if is_open else "\u201d")
            continue

        if ch == "'":
            prev = _prev_nonspace(i)
            nxt = _next_nonspace(i)
            # Apostrophe in the middle of a word.
            if prev.isalnum() and nxt.isalnum():
                out.append("\u2019")
                continue
            is_open = (not prev) or prev in "([{" or prev in "\n\r\t" or prev == "-"
            if not nxt or nxt in ")]}.,:;!?":
                is_open = False
            out.append("\u2018" if is_open else "\u2019")
            continue

        out.append(ch)

    return "".join(out)


def _apply_typography_to_text(text: str) -> str:
    """Apply HackMD-like typographic replacements to plain text."""

    if not text:
        return text

    s = text

    # Symbols.
    s = re.sub(r"\((?:c)\)", "\u00a9", s, flags=re.IGNORECASE)
    s = re.sub(r"\((?:r)\)", "\u00ae", s, flags=re.IGNORECASE)
    s = re.sub(r"\((?:tm)\)", "\u2122", s, flags=re.IGNORECASE)
    s = re.sub(r"\((?:p)\)", "\u00a7", s, flags=re.IGNORECASE)
    s = s.replace("+-", "\u00b1")

    # Punctuation.
    s = s.replace("---", "\u2014")  # em dash
    s = s.replace("--", "\u2013")  # en dash
    s = re.sub(r"\.{3}", "\u2026", s)  # ellipsis

    # Collapse excessive punctuation (HackMD-like).
    s = re.sub(r"!{4,}", "!!!", s)
    s = re.sub(r"\?{4,}", "???", s)
    s = re.sub(r",{2,}", ",", s)

    # Quotes.
    s = _smart_quotes(s)

    return s


def apply_hackmd_typography(markdown_text: str) -> str:
    """Apply HackMD-like typography substitutions to markdown.

    - Skips fenced code blocks and inline code spans.
    - Leaves embed directives `{% ... %}` untouched.
    """

    text = markdown_text or ""
    out_parts: list[str] = []

    # Be tolerant like HackMD/markdown-it: allow 1+ dashes.
    # We will normalize to 3 dashes later so remark-gfm reliably parses tables.
    _TABLE_DELIM_RE = re.compile(
        r"^\s*\|?\s*:?-{1,}:?\s*(\|\s*:?-{1,}:?\s*)+\|?\s*$"
    )

    _TABLE_CELL_RE = re.compile(r"(?P<lead>\|\s*)(?P<cell>:?-{1,}:?)(?=\s*\||\s*$)")

    def _normalize_table_delim_line(line: str) -> str:
        """Normalize a GFM table delimiter line.

        HackMD accepts as few as 1 dash; remark-gfm expects 3+. To make preview match
        HackMD behavior, we keep alignment markers but pad dashes to at least 3.
        """

        raw = line.rstrip("\r\n")
        suffix = line[len(raw) :]

        def _pad(cell: str) -> str:
            left = ":" if cell.startswith(":") else ""
            right = ":" if cell.endswith(":") else ""
            dash_count = max(0, len(cell) - len(left) - len(right))
            dashes = "-" * max(3, dash_count)
            return f"{left}{dashes}{right}"

        # Ensure the line has leading/trailing pipes for consistent parsing.
        if "|" not in raw:
            return line

        s = raw
        if not s.strip().startswith("|"):
            s = "|" + s
        if not s.strip().endswith("|"):
            s = s + "|"

        def _repl(m: re.Match[str]) -> str:
            return f"{m.group('lead')}{_pad(m.group('cell'))}"

        s = _TABLE_CELL_RE.sub(_repl, s)
        return s + suffix

    def _iter_table_aware_parts(buf: str) -> list[tuple[bool, str]]:
        """Split a string into (is_table, text) parts.

        This prevents typography transforms from breaking GFM tables.
        """

        if not buf:
            return [(False, buf)]

        lines = buf.splitlines(keepends=True)
        parts: list[tuple[bool, str]] = []
        i = 0

        def _is_header_line(line: str) -> bool:
            s = line.strip()
            if "|" not in s:
                return False
            # Require some non-syntax content.
            return any(ch not in "|:- " for ch in s)

        def _is_delim_line(line: str) -> bool:
            return _TABLE_DELIM_RE.match(line.rstrip("\r\n")) is not None

        while i < len(lines):
            if i + 1 < len(lines) and _is_header_line(lines[i]) and _is_delim_line(lines[i + 1]):
                start = i
                # Normalize delimiter line to keep table parsing stable.
                lines[i + 1] = _normalize_table_delim_line(lines[i + 1])
                i += 2
                while i < len(lines) and lines[i].strip() and ("|" in lines[i]):
                    i += 1
                parts.append((True, "".join(lines[start:i])))
                continue

            # Normal text: accumulate until next table start.
            start = i
            i += 1
            while i < len(lines):
                if i + 1 < len(lines) and _is_header_line(lines[i]) and _is_delim_line(lines[i + 1]):
                    break
                i += 1
            parts.append((False, "".join(lines[start:i])))

        return parts

    def _process_noncode(segment: str) -> str:
        if not segment:
            return segment

        # Do not transform inside embed directives.
        parts: list[str] = []
        pos = 0
        for m in _DIRECTIVE_RE.finditer(segment):
            before = segment[pos : m.start()]
            raw = m.group(0)
            parts.append(before)
            parts.append(raw)
            pos = m.end()
        parts.append(segment[pos:])

        # Apply typography to each non-directive chunk, preserving inline code and tables.
        for i, chunk in enumerate(parts):
            if i % 2 == 1:
                out_parts.append(chunk)
                continue

            for is_table, buf in _iter_table_aware_parts(chunk):
                if is_table:
                    out_parts.append(buf)
                    continue

                # Split on inline code spans (backticks) and only transform non-code.
                j = 0
                while j < len(buf):
                    tick = buf.find("`", j)
                    if tick == -1:
                        out_parts.append(_apply_typography_to_text(buf[j:]))
                        break
                    # Find matching tick.
                    end = buf.find("`", tick + 1)
                    if end == -1:
                        out_parts.append(_apply_typography_to_text(buf[j:]))
                        break
                    out_parts.append(_apply_typography_to_text(buf[j:tick]))
                    out_parts.append(buf[tick : end + 1])
                    j = end + 1
        return ""

    # Robust fenced-block skipping: supports 3+ backticks/tildes and won't be confused by
    # longer fences like ````` used to show ``` literally.
    fence_open_re = re.compile(r"^(?P<indent>\s{0,3})(?P<fence>`{3,}|~{3,})(?P<info>.*)$")
    lines = text.splitlines(keepends=True)
    i = 0
    buf: list[str] = []

    def _flush_buf():
        if not buf:
            return
        _process_noncode("".join(buf))
        buf.clear()

    while i < len(lines):
        line = lines[i].rstrip("\r\n")
        m_open = fence_open_re.match(line)
        if not m_open:
            buf.append(lines[i])
            i += 1
            continue

        _flush_buf()

        indent = m_open.group("indent")
        fence = m_open.group("fence")
        fence_char = fence[0]
        fence_len = len(fence)
        close_re = re.compile(rf"^{re.escape(indent)}{re.escape(fence_char)}{{{fence_len},}}\s*$")

        out_parts.append(lines[i])
        i += 1
        while i < len(lines) and not close_re.match(lines[i].rstrip("\r\n")):
            out_parts.append(lines[i])
            i += 1
        if i < len(lines):
            out_parts.append(lines[i])
            i += 1

    _flush_buf()
    return "".join(out_parts)


_CODE_FENCE_RE = re.compile(
    # Only match *exactly* triple-backtick fences. See `_FENCED_BLOCK_RE`.
    r"```(?!`)(?P<info>[^\n]*)\r?\n(?P<body>.*?)(?:\r?\n)```(?!`)",
    re.DOTALL,
)


def apply_hackmd_code_fence_options(markdown_text: str) -> str:
    """Apply HackMD-like code fence options.

    Supports (HackMD-style), rewritten into a markdown-parser-friendly first token:
    - ```lang=101  -> ```lang-linenos-101
    - ```lang=     -> ```lang-linenos-1
    - ```lang=+    -> ```lang-linenos-<previous_end+1>
    - ```lang!     -> ```lang-wrap
    - ```!         -> ```markdown-wrap

    This function rewrites the fence info string only; it does not modify code content.
    """

    text = markdown_text or ""
    last_end_line: int | None = None

    fence_open_re = re.compile(r"^(?P<indent>\s{0,3})(?P<fence>`{3,}|~{3,})(?P<info>.*)$")
    lines = text.splitlines(keepends=True)
    out: list[str] = []
    i = 0

    def _count_body_lines(body_lines: list[str]) -> int:
        return len(body_lines)

    while i < len(lines):
        line = lines[i].rstrip("\r\n")
        m_open = fence_open_re.match(line)
        if not m_open:
            out.append(lines[i])
            i += 1
            continue

        indent = m_open.group("indent")
        fence = m_open.group("fence")
        info = (m_open.group("info") or "").rstrip("\r")
        fence_char = fence[0]
        fence_len = len(fence)
        close_re = re.compile(rf"^{re.escape(indent)}{re.escape(fence_char)}{{{fence_len},}}\s*$")

        j = i + 1
        body_lines: list[str] = []
        while j < len(lines) and not close_re.match(lines[j].rstrip("\r\n")):
            body_lines.append(lines[j])
            j += 1

        # No closing fence: emit verbatim.
        if j >= len(lines):
            out.append(lines[i])
            out.extend(body_lines)
            break

        stripped = info.strip()
        if stripped:
            parts = stripped.split(None, 1)
            token = parts[0]
            rest = parts[1] if len(parts) > 1 else ""

            wrap = False
            if token.endswith("!"):
                wrap = True
                token = token[:-1]
            if wrap and not token:
                token = "markdown"

            start_line: int | None = None
            if "=" in token:
                base, opt = token.split("=", 1)
                base = base.strip()
                opt = opt.strip()
                if opt == "+":
                    start_line = (last_end_line + 1) if last_end_line else 1
                elif opt.isdigit():
                    start_line = int(opt)
                else:
                    start_line = 1
                token = base

            out_token = token
            if start_line is not None:
                out_token = f"{token}-linenos-{start_line}"
            if wrap:
                out_token = f"{out_token}-wrap" if out_token else "markdown-wrap"

            new_info = out_token if not rest else f"{out_token} {rest}".rstrip()
            line_end = lines[i][len(lines[i].rstrip("\r\n")) :]
            out.append(f"{indent}{fence}{new_info}{line_end}")

            if start_line is not None:
                count = _count_body_lines(body_lines)
                if count > 0:
                    last_end_line = start_line + count - 1
                else:
                    last_end_line = start_line
        else:
            out.append(lines[i])

        out.extend(body_lines)
        out.append(lines[j])
        i = j + 1

    return "".join(out)


def apply_hackmd_code_blocks_with_lines(markdown_text: str) -> str:
    """Render fenced code blocks into HTML with syntax highlighting and optional line numbers.

    This is the pragmatic way to support HackMD-style options in Reflex today:
    - `=`, `=101`, `=+` (already normalized by `apply_hackmd_code_fence_options`) -> line numbers
    - `!` (normalized to `-wrap`) -> wrap long lines

    Output is raw HTML that relies on `rehypeRaw` (already enabled) to render.
    """

    text = markdown_text or ""

    try:
        from pygments import highlight  # type: ignore
        from pygments.formatters.html import HtmlFormatter  # type: ignore
        from pygments.lexers import get_lexer_by_name  # type: ignore
        from pygments.lexers.special import TextLexer  # type: ignore
    except Exception:
        # If pygments isn't installed, keep the markdown as-is.
        return text

    aliases = {
        "js": "javascript",
        "ts": "typescript",
        "py": "python",
        "sh": "bash",
        "shell": "bash",
        "zsh": "bash",
        "yml": "yaml",
        "md": "markdown",
        "html": "html",
        "xml": "xml",
        "c++": "cpp",
        "c#": "csharp",
        "ps1": "powershell",
        "console": "text",
    }

    fence_open_re = re.compile(
        r"^(?P<indent>\s{0,3})(?P<fence>`{3,}|~{3,})(?P<info>.*)$"
    )

    lines = text.splitlines(keepends=True)
    out: list[str] = []
    i = 0

    def _parse_info(info: str) -> tuple[str, bool, bool, int]:
        """Return (language, wrap, show_linenos, linenostart)."""

        stripped = (info or "").strip()
        if not stripped:
            return ("text", False, False, 1)

        token = stripped.split(None, 1)[0]
        wrap = False
        if token.endswith("-wrap"):
            wrap = True
            token = token[: -len("-wrap")]

        show_linenos = False
        linenostart = 1
        m_ln = re.match(r"^(?P<base>.+?)-linenos-(?P<start>\d+)$", token, flags=re.IGNORECASE)
        if m_ln:
            show_linenos = True
            linenostart = int(m_ln.group("start"))
            token = m_ln.group("base")

        lang = aliases.get(token.strip().lower(), token.strip().lower())
        if not lang:
            lang = "text"

        return (lang, wrap, show_linenos, linenostart)

    def _render_block(info: str, code: str) -> str:
        lang, wrap, show_linenos, linenostart = _parse_info(info)

        try:
            lexer = get_lexer_by_name(lang)
        except Exception:
            lexer = TextLexer()

        formatter = HtmlFormatter(
            linenos="table" if show_linenos else False,
            linenostart=linenostart,
            noclasses=True,
        )

        highlighted = highlight(code, lexer, formatter)
        # Ensure the block scrolls horizontally by default.
        # If wrap is requested, allow wrapping inside <pre>.
        if wrap:
            # Add `white-space: pre-wrap` into the first <pre ...> style.
            highlighted = re.sub(
                r"(<pre\b[^>]*style=\")",
                r"\1white-space: pre-wrap; word-break: break-word; ",
                highlighted,
                count=1,
                flags=re.IGNORECASE,
            )
            # If there was no inline style attribute, add one.
            highlighted = re.sub(
                r"(<pre\b(?![^>]*style=))",
                r"\1 style=\"white-space: pre-wrap; word-break: break-word;\"",
                highlighted,
                count=1,
                flags=re.IGNORECASE,
            )

        return (
            "<div style=\"margin-top: 1em; margin-bottom: 1em; overflow-x: auto;\">"
            + highlighted
            + "</div>"
        )

    while i < len(lines):
        line = lines[i].rstrip("\r\n")
        m_open = fence_open_re.match(line)
        if not m_open:
            out.append(lines[i])
            i += 1
            continue

        indent = m_open.group("indent")
        fence = m_open.group("fence")
        fence_char = fence[0]
        fence_len = len(fence)
        info = m_open.group("info") or ""
        j = i + 1
        body_lines: list[str] = []

        fence_close_re = re.compile(
            rf"^{re.escape(indent)}{re.escape(fence_char)}{{{fence_len},}}\s*$"
        )
        while j < len(lines) and not fence_close_re.match(lines[j].rstrip("\r\n")):
            body_lines.append(lines[j])
            j += 1

        # No closing fence: treat as normal text.
        if j >= len(lines):
            out.append(lines[i])
            out.extend(body_lines)
            break

        code = "".join(body_lines)
        code = code.rstrip("\r\n")
        out.append(_render_block(info, code) + "\n")
        i = j + 1

    return "".join(out)


def _fetch_oembed_html(*, endpoint: str, target_url: str) -> str | None:
    """Fetch oEmbed HTML with a tiny in-memory cache."""

    cache_key = f"{endpoint}|{target_url}"
    now = time.time()
    cached = _OEMBED_CACHE.get(cache_key)
    if cached and now - cached[0] < _OEMBED_TTL_S:
        return cached[1]

    full_url = endpoint
    if "?" in endpoint:
        full_url = endpoint + "&" + urlencode({"url": target_url, "format": "json"})
    else:
        full_url = endpoint + "?" + urlencode({"url": target_url, "format": "json"})

    try:
        req = Request(full_url, headers={"User-Agent": "codoc-in-md"})
        with urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None

    html_snippet = data.get("html") if isinstance(data, dict) else None
    if isinstance(html_snippet, str) and html_snippet.strip():
        _OEMBED_CACHE[cache_key] = (now, html_snippet)
        return html_snippet
    return None


_GIST_CACHE: dict[str, tuple[float, str]] = {}


def _build_gist_js_url(value: str) -> str | None:
    v = (value or "").strip()
    if not v:
        return None

    # HackMD shorthand: user/gist_id
    if re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9]+", v):
        return f"https://gist.github.com/{v}.js"

    # Full gist URL.
    if v.lower().startswith("https://"):
        try:
            parsed = urlparse(v)
        except Exception:
            return None
        host = (parsed.netloc or "").lower()
        if "gist.github.com" not in host:
            return None

        # Ensure the `.js` suffix is applied to the *path* (not appended after query
        # params like `?file=...`). Preserve any existing query string.
        path = (parsed.path or "").rstrip("/")
        if not path:
            return None
        if not path.endswith(".js"):
            path = path + ".js"
        return urlunparse(
            (
                parsed.scheme,
                parsed.netloc,
                path,
                parsed.params,
                parsed.query,
                parsed.fragment,
            )
        )

    return None


def _extract_gist_id(value: str) -> str | None:
    v = (value or "").strip()
    if not v:
        return None

    # HackMD shorthand: user/gist_id
    if re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9]+", v):
        return v.split("/", 1)[1]

    # Full gist URL.
    if v.lower().startswith("https://"):
        try:
            parsed = urlparse(v)
        except Exception:
            return None
        host = (parsed.netloc or "").lower()
        if "gist.github.com" not in host:
            return None
        parts = [p for p in (parsed.path or "").split("/") if p]
        if not parts:
            return None
        candidate = parts[-1]
        if candidate.endswith(".js"):
            candidate = candidate[: -len(".js")]
        return candidate or None

    return None


def _fetch_gist_html(gist_id: str) -> str | None:
    now = time.time()
    cached = _GIST_CACHE.get(gist_id)
    if cached and now - cached[0] < _OEMBED_TTL_S:
        return cached[1]

    api_url = f"https://api.github.com/gists/{gist_id}"
    try:
        req = Request(
            api_url,
            headers={
                "User-Agent": "codoc-in-md",
                "Accept": "application/vnd.github+json",
            },
        )
        with urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None

    files = (data or {}).get("files") if isinstance(data, dict) else None
    if not isinstance(files, dict) or not files:
        return None

    parts: list[str] = ["<div class=\"my-4 w-full\">"]
    for filename, meta in files.items():
        if not isinstance(meta, dict):
            continue
        content = meta.get("content")
        if not isinstance(content, str):
            continue
        safe_name = html.escape(str(filename), quote=True)
        safe_content = html.escape(content)
        parts.append(
            f"<div class=\"mb-3\"><div class=\"text-sm font-semibold text-gray-700 mb-1\">{safe_name}</div>"
        )
        parts.append(
            "<pre class=\"overflow-auto text-sm bg-gray-50 border border-gray-200 rounded p-3\">"
            f"{safe_content}</pre></div>"
        )
    parts.append("</div>")

    rendered = "".join(parts)
    _GIST_CACHE[gist_id] = (now, rendered)
    return rendered


class YouTubeEmbed:
    name = "youtube"

    def render(self, directive: EmbedDirective) -> str | None:
        video_id = _extract_youtube_id((directive.args or "").strip())
        if not video_id:
            return None

        embed_url = f"https://www.youtube.com/embed/{video_id}"

        # Inline CSS for reliable aspect ratio (no Tailwind plugin dependency and avoids
        # accidental <p> wrapping collapsing the iframe height).
        return (
            "\n<div class=\"my-4 w-full\" "
            "style=\"position:relative;padding-bottom:56.25%;height:0;overflow:hidden;\">"
            f"<iframe src=\"{embed_url}\" "
            "title=\"YouTube video\" frameborder=\"0\" "
            "allow=\"accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share\" "
            "allowfullscreen "
            "style=\"position:absolute;top:0;left:0;width:100%;height:100%;\"></iframe>"
            "</div>\n"
        )


class VimeoEmbed:
    name = "vimeo"

    def render(self, directive: EmbedDirective) -> str | None:
        value = (directive.args or "").strip()
        if not value:
            return None

        # Accept either numeric ID or a vimeo URL.
        video_id: str | None = None
        if re.fullmatch(r"\d{3,20}", value):
            video_id = value
        else:
            try:
                parsed = urlparse(value)
            except Exception:
                return None
            host = (parsed.netloc or "").lower()
            if "vimeo.com" not in host:
                return None
            candidate = (parsed.path or "").strip("/").split("/", 1)[0]
            if re.fullmatch(r"\d{3,20}", candidate):
                video_id = candidate

        if not video_id:
            return None

        embed_url = f"https://player.vimeo.com/video/{video_id}"
        return (
            "\n<div class=\"my-4 w-full\" "
            "style=\"position:relative;padding-bottom:56.25%;height:0;overflow:hidden;\">"
            f"<iframe src=\"{embed_url}\" "
            "title=\"Vimeo video\" frameborder=\"0\" allow=\"autoplay; fullscreen; picture-in-picture\" "
            "allowfullscreen "
            "style=\"position:absolute;top:0;left:0;width:100%;height:100%;\"></iframe>"
            "</div>\n"
        )


class PdfEmbed:
    name = "pdf"

    def render(self, directive: EmbedDirective) -> str | None:
        url = (directive.args or "").strip()
        if not url:
            return None
        if not url.lower().startswith("https://"):
            return None

        # Many sites block being embedded in an iframe (X-Frame-Options/CSP).
        # Proxy via the backend so the iframe is same-origin.
        base = _backend_base_url()
        query = urlencode({"url": url})
        iframe_src = f"{base}/__embed/pdf?{query}"
        safe_url = html.escape(iframe_src, quote=True)
        return (
            "\n<div class=\"my-4 w-full\">"
            f"<iframe src=\"{safe_url}\" title=\"PDF\" "
            "style=\"width:100%;height:600px;border:0;\"></iframe>"
            "</div>\n"
        )


class GenericIFrameEmbed:
    """Best-effort iframe embed for providers that require an embed URL."""

    def __init__(self, name: str, *, title: str, height_px: int = 480):
        self.name = name
        self._title = title
        self._height_px = height_px

    def render(self, directive: EmbedDirective) -> str | None:
        url = (directive.args or "").strip()
        if not url or not url.lower().startswith("https://"):
            return None

        safe_url = html.escape(url, quote=True)
        safe_title = html.escape(self._title, quote=True)
        return (
            "\n<div class=\"my-4 w-full\">"
            f"<iframe src=\"{safe_url}\" title=\"{safe_title}\" "
            f"style=\"width:100%;height:{self._height_px}px;border:0;\"></iframe>"
            "</div>\n"
        )


class GistEmbed:
    name = "gist"

    def render(self, directive: EmbedDirective) -> str | None:
        value = (directive.args or "").strip()
        if not value:
            return None

        # Prefer the official gist embed script via backend static HTML.
        # This matches HackMD/GitHub behavior and avoids markdown parsing issues
        # (e.g. lines starting with `#` becoming headings).
        gist_js = _build_gist_js_url(value)
        if gist_js:
            base = _backend_base_url()
            query = urlencode({"url": gist_js})
            iframe_src = f"{base}/__embed/gist?{query}"
            return (
                "\n<div class=\"my-4 w-full\">"
                "<iframe sandbox=\"allow-scripts allow-same-origin\" "
                "style=\"width:100%;height:600px;border:0;\" "
                f"src=\"{html.escape(iframe_src, quote=True)}\"></iframe>"
                "</div>\n"
            )

        # Fallback: server-side rendering via GitHub API (no iframe).
        gist_id = _extract_gist_id(value)
        if gist_id:
            rendered = _fetch_gist_html(gist_id)
            if rendered:
                return "\n" + rendered + "\n"

        # Last resort: link only.
        safe_value = html.escape(value, quote=True)
        return (
            "\n<div class=\"my-4\">"
            f"<a href=\"{safe_value}\" target=\"_blank\" rel=\"noreferrer\">"
            f"Gist {html.escape(value)}"
            "</a></div>\n"
        )


def register_backend_embed_routes(app: rx.App) -> None:
    """Register backend (port 8000) embed endpoints.

    These return static HTML so third-party scripts like GitHub Gist (document.write)
    execute reliably when loaded in an iframe.
    """

    def _embed_html(body: str) -> str:
        return (
            "<!doctype html><html><head><meta charset='utf-8'/>"
            "<meta name='viewport' content='width=device-width, initial-scale=1'/>"
            "<style>body{margin:0;padding:0;font-family:sans-serif}</style>"
            "</head><body>"
            f"{body}"
            "</body></html>"
        )

    def _get_code(request: StarletteRequest) -> str:
        """Read code from query params.

        Prefer `b64` to avoid URL-encoding issues for multi-line blocks.
        """

        b64 = (request.query_params.get("b64") or "").strip()
        if b64:
            try:
                padded = b64 + "=" * (-len(b64) % 4)
                return base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8")
            except (binascii.Error, UnicodeDecodeError):
                return ""
        return (request.query_params.get("code") or "").strip()

    def _api_embed_gist(request: StarletteRequest) -> HTMLResponse:
        url = (request.query_params.get("url") or "").strip()
        if not url or not url.lower().startswith("https://"):
            return HTMLResponse(_embed_html("<pre>Invalid gist URL</pre>"))

        safe = (
            url.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#x27;")
        )
        body = (
            "<style>body{margin:0;padding:0} .gist{font-size:12px}</style>"
            f"<script src='{safe}'></script>"
        )
        return HTMLResponse(_embed_html(body))

    def _api_embed_sequence(request: StarletteRequest) -> HTMLResponse:
        code = _get_code(request)
        if not code:
            return HTMLResponse(_embed_html("<pre>(empty)</pre>"))

        safe_code = (
            code.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        body = (
            "<div id='diagram'></div>"
            f"<pre id='source' style='display:none'>{safe_code}</pre>"
            "<script src='https://bramp.github.io/js-sequence-diagrams/js/webfont.js'></script>"
            "<script src='https://bramp.github.io/js-sequence-diagrams/js/snap.svg-min.js'></script>"
            "<script src='https://bramp.github.io/js-sequence-diagrams/js/underscore-min.js'></script>"
            "<script src='https://bramp.github.io/js-sequence-diagrams/js/sequence-diagram-min.js'></script>"
            "<script>(function(){try{var text=document.getElementById('source').textContent;"
            "var d=Diagram.parse(text);d.drawSVG('diagram',{theme:'simple'});}catch(e){"
            "var pre=document.createElement('pre');pre.textContent=text;document.body.appendChild(pre);}})();</script>"
        )
        return HTMLResponse(_embed_html(body))

    def _api_embed_flow(request: StarletteRequest) -> HTMLResponse:
        code = _get_code(request)
        if not code:
            return HTMLResponse(_embed_html("<pre>(empty)</pre>"))

        safe_code = (
            code.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        body = (
            "<style>#diagram svg{max-width:100%;height:auto}</style>"
            "<div id='diagram'></div>"
            f"<pre id='source' style='display:none'>{safe_code}</pre>"
            "<script src='https://cdnjs.cloudflare.com/ajax/libs/raphael/2.3.0/raphael.min.js'></script>"
            "<script src='https://cdnjs.cloudflare.com/ajax/libs/flowchart/1.17.1/flowchart.min.js'></script>"
            "<script>(function(){var text=document.getElementById('source').textContent;"
            "try{var diagram=flowchart.parse(text);diagram.drawSVG('diagram');}"
            "catch(e){var pre=document.createElement('pre');pre.textContent=text;document.body.appendChild(pre);}})();</script>"
        )
        return HTMLResponse(_embed_html(body))

    def _api_embed_graphviz(request: StarletteRequest) -> HTMLResponse:
        code = _get_code(request)
        if not code:
            return HTMLResponse(_embed_html("<pre>(empty)</pre>"))

        safe_code = (
            code.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        body = (
            "<style>#diagram svg{max-width:100%;height:auto}</style>"
            "<div id='diagram'></div>"
            f"<pre id='source' style='display:none'>{safe_code}</pre>"
            "<script src='https://cdn.jsdelivr.net/npm/viz.js@2.1.2/viz.js'></script>"
            "<script src='https://cdn.jsdelivr.net/npm/viz.js@2.1.2/full.render.js'></script>"
            "<script>(function(){var text=document.getElementById('source').textContent;"
            "var container=document.getElementById('diagram');"
            "try{var viz=new Viz();viz.renderSVGElement(text).then(function(el){container.appendChild(el);})"
            ".catch(function(){var pre=document.createElement('pre');pre.textContent=text;document.body.appendChild(pre);});}"
            "catch(e){var pre=document.createElement('pre');pre.textContent=text;document.body.appendChild(pre);}})();</script>"
        )
        return HTMLResponse(_embed_html(body))

    def _api_embed_mermaid(request: StarletteRequest) -> HTMLResponse:
        code = _get_code(request)
        if not code:
            return HTMLResponse(_embed_html("<pre>(empty)</pre>"))

        safe_code = (
            code.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        body = (
            "<style>#diagram svg{max-width:100%;height:auto}</style>"
            "<div id='diagram' class='mermaid'></div>"
            f"<pre id='source' style='display:none'>{safe_code}</pre>"
            "<script src='https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js'></script>"
            "<script>(function(){var el=document.getElementById('diagram');"
            "el.textContent=document.getElementById('source').textContent;"
            "try{mermaid.initialize({startOnLoad:false});mermaid.init(undefined, el);}"
            "catch(e){var pre=document.createElement('pre');pre.textContent=el.textContent;document.body.appendChild(pre);}})();</script>"
        )
        return HTMLResponse(_embed_html(body))

    def _api_embed_abc(request: StarletteRequest) -> HTMLResponse:
        code = _get_code(request)
        if not code:
            return HTMLResponse(_embed_html("<pre>(empty)</pre>"))

        safe_code = (
            code.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        body = (
            "<style>#paper svg{max-width:100%;height:auto}</style>"
            "<div id='paper'></div>"
            f"<pre id='source' style='display:none'>{safe_code}</pre>"
            "<script src='https://cdn.jsdelivr.net/npm/abcjs@6.2.3/dist/abcjs-basic-min.js'></script>"
            "<script>(function(){var text=document.getElementById('source').textContent;"
            "try{ABCJS.renderAbc('paper', text, {responsive:'resize'});}"
            "catch(e){var pre=document.createElement('pre');pre.textContent=text;document.body.appendChild(pre);}})();</script>"
        )
        return HTMLResponse(_embed_html(body))

    def _api_embed_vega(request: StarletteRequest) -> HTMLResponse:
        code = _get_code(request)
        if not code:
            return HTMLResponse(_embed_html("<pre>(empty)</pre>"))

        safe_code = (
            code.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        body = (
            "<div id='vis'></div>"
            f"<pre id='source' style='display:none'>{safe_code}</pre>"
            "<script src='https://cdn.jsdelivr.net/npm/vega@5/build/vega.min.js'></script>"
            "<script src='https://cdn.jsdelivr.net/npm/vega-lite@5/build/vega-lite.min.js'></script>"
            "<script src='https://cdn.jsdelivr.net/npm/vega-embed@6/build/vega-embed.min.js'></script>"
            "<script>(function(){var text=document.getElementById('source').textContent;"
            "var target=document.getElementById('vis');var spec=null;"
            "try{spec=JSON.parse(text);}catch(e){var pre=document.createElement('pre');pre.textContent='Invalid JSON';document.body.appendChild(pre);return;}"
            "try{vegaEmbed(target, spec, {actions:false}).catch(function(){var pre=document.createElement('pre');pre.textContent=text;document.body.appendChild(pre);});}"
            "catch(e){var pre=document.createElement('pre');pre.textContent=text;document.body.appendChild(pre);}})();</script>"
        )
        return HTMLResponse(_embed_html(body))

    def _api_embed_pdf(request: StarletteRequest) -> Response:
        url = (request.query_params.get("url") or "").strip()
        if not url or not url.lower().startswith("https://"):
            return HTMLResponse(_embed_html("<pre>Invalid PDF URL</pre>"))

        try:
            parsed = urlparse(url)
        except Exception:
            return HTMLResponse(_embed_html("<pre>Invalid PDF URL</pre>"))

        host = (parsed.hostname or "").strip()
        if not host:
            return HTMLResponse(_embed_html("<pre>Invalid PDF URL</pre>"))

        # Basic SSRF protections.
        host_l = host.lower()
        if host_l in {"localhost"} or host_l.endswith(".local"):
            return HTMLResponse(_embed_html("<pre>Blocked host</pre>"))

        try:
            ip = ipaddress.ip_address(host)
            if (
                ip.is_private
                or ip.is_loopback
                or ip.is_link_local
                or ip.is_multicast
                or ip.is_reserved
            ):
                return HTMLResponse(_embed_html("<pre>Blocked host</pre>"))
        except ValueError:
            # Not an IP literal; allow hostname.
            pass

        # Avoid non-standard ports.
        if parsed.port not in (None, 443):
            return HTMLResponse(_embed_html("<pre>Blocked port</pre>"))

        try:
            req = Request(url, headers={"User-Agent": "codoc-in-md"})
            with urlopen(req, timeout=10) as resp:
                content_type = (resp.headers.get("Content-Type") or "").lower()
                max_bytes = 15 * 1024 * 1024
                chunks: list[bytes] = []
                total = 0
                while True:
                    chunk = resp.read(64 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > max_bytes:
                        return HTMLResponse(_embed_html("<pre>PDF too large</pre>"))
                    chunks.append(chunk)
        except Exception:
            return HTMLResponse(_embed_html("<pre>Failed to fetch PDF</pre>"))

        # Best-effort content-type validation (some servers mislabel PDFs).
        if "application/pdf" not in content_type and not (parsed.path or "").lower().endswith(".pdf"):
            return HTMLResponse(_embed_html("<pre>URL is not a PDF</pre>"))

        data = b"".join(chunks)
        return Response(
            content=data,
            media_type="application/pdf",
            headers={"Content-Disposition": "inline"},
        )

    existing_paths = {getattr(r, "path", None) for r in getattr(app._api, "routes", [])}
    if "/__embed/gist" not in existing_paths:
        app._api.add_route("/__embed/gist", _api_embed_gist, methods=["GET"])
    if "/__embed/sequence" not in existing_paths:
        app._api.add_route("/__embed/sequence", _api_embed_sequence, methods=["GET"])
    if "/__embed/flow" not in existing_paths:
        app._api.add_route("/__embed/flow", _api_embed_flow, methods=["GET"])
    if "/__embed/graphviz" not in existing_paths:
        app._api.add_route("/__embed/graphviz", _api_embed_graphviz, methods=["GET"])
    if "/__embed/mermaid" not in existing_paths:
        app._api.add_route("/__embed/mermaid", _api_embed_mermaid, methods=["GET"])
    if "/__embed/abc" not in existing_paths:
        app._api.add_route("/__embed/abc", _api_embed_abc, methods=["GET"])
    if "/__embed/vega" not in existing_paths:
        app._api.add_route("/__embed/vega", _api_embed_vega, methods=["GET"])
    if "/__embed/pdf" not in existing_paths:
        app._api.add_route("/__embed/pdf", _api_embed_pdf, methods=["GET"])


class SlideShareEmbed:
    name = "slideshare"

    def render(self, directive: EmbedDirective) -> str | None:
        value = (directive.args or "").strip()
        if not value:
            return None

        url = value
        if not url.lower().startswith("https://"):
            # HackMD shorthand like `user/slug`.
            url = f"https://www.slideshare.net/{url.lstrip('/')}"

        html_snippet = _fetch_oembed_html(
            endpoint="https://www.slideshare.net/api/oembed/2",
            target_url=url,
        )
        if html_snippet:
            return f"\n<div class=\"my-4 w-full\">{html_snippet}</div>\n"

        # Fallback: try iframing the URL.
        safe_url = html.escape(url, quote=True)
        return (
            "\n<div class=\"my-4 w-full\">"
            f"<iframe src=\"{safe_url}\" title=\"SlideShare\" "
            "style=\"width:100%;height:520px;border:0;\"></iframe>"
            "</div>\n"
        )


class SpeakerDeckEmbed:
    name = "speakerdeck"

    def render(self, directive: EmbedDirective) -> str | None:
        value = (directive.args or "").strip()
        if not value:
            return None

        url = value
        if not url.lower().startswith("https://"):
            url = f"https://speakerdeck.com/{url.lstrip('/')}"

        html_snippet = _fetch_oembed_html(
            endpoint="https://speakerdeck.com/oembed.json",
            target_url=url,
        )
        if html_snippet:
            return f"\n<div class=\"my-4 w-full\">{html_snippet}</div>\n"

        safe_url = html.escape(url, quote=True)
        return (
            "\n<div class=\"my-4 w-full\">"
            f"<iframe src=\"{safe_url}\" title=\"SpeakerDeck\" "
            "style=\"width:100%;height:520px;border:0;\"></iframe>"
            "</div>\n"
        )


class SequenceDiagramBlock:
    language = "sequence"

    def render(self, block: FencedCodeBlock) -> str | None:
        # Prefer using a first-party endpoint for rendering, because markdown sanitizers
        # often strip iframe[srcdoc].
        base = _backend_base_url()
        query = urlencode({"b64": _encode_code_b64(block.code)})
        iframe_src = f"{base}/__embed/sequence?{query}"
        return (
            "\n<div class=\"my-4 w-full\">"
            "<iframe sandbox=\"allow-scripts allow-same-origin\" "
            "style=\"width:100%;height:360px;border:0;\" "
            f"src=\"{html.escape(iframe_src, quote=True)}\"></iframe>"
            "</div>\n"
        )


class FlowChartBlock:
    language = "flow"

    def render(self, block: FencedCodeBlock) -> str | None:
        base = _backend_base_url()
        query = urlencode({"b64": _encode_code_b64(block.code)})
        iframe_src = f"{base}/__embed/flow?{query}"
        return (
            "\n<div class=\"my-4 w-full\">"
            "<iframe sandbox=\"allow-scripts allow-same-origin\" "
            "style=\"width:100%;height:420px;border:0;\" "
            f"src=\"{html.escape(iframe_src, quote=True)}\"></iframe>"
            "</div>\n"
        )


class GraphvizBlock:
    language = "graphviz"

    def render(self, block: FencedCodeBlock) -> str | None:
        base = _backend_base_url()
        query = urlencode({"b64": _encode_code_b64(block.code)})
        iframe_src = f"{base}/__embed/graphviz?{query}"
        return (
            "\n<div class=\"my-4 w-full\">"
            "<iframe sandbox=\"allow-scripts allow-same-origin\" "
            "style=\"width:100%;height:420px;border:0;\" "
            f"src=\"{html.escape(iframe_src, quote=True)}\"></iframe>"
            "</div>\n"
        )


class MermaidBlock:
    language = "mermaid"

    def render(self, block: FencedCodeBlock) -> str | None:
        base = _backend_base_url()
        query = urlencode({"b64": _encode_code_b64(block.code)})
        iframe_src = f"{base}/__embed/mermaid?{query}"
        return (
            "\n<div class=\"my-4 w-full\">"
            "<iframe sandbox=\"allow-scripts allow-same-origin\" "
            "style=\"width:100%;height:420px;border:0;\" "
            f"src=\"{html.escape(iframe_src, quote=True)}\"></iframe>"
            "</div>\n"
        )


class AbcBlock:
    language = "abc"

    def render(self, block: FencedCodeBlock) -> str | None:
        base = _backend_base_url()
        query = urlencode({"b64": _encode_code_b64(block.code)})
        iframe_src = f"{base}/__embed/abc?{query}"
        return (
            "\n<div class=\"my-4 w-full\">"
            "<iframe sandbox=\"allow-scripts allow-same-origin\" "
            "style=\"width:100%;height:420px;border:0;\" "
            f"src=\"{html.escape(iframe_src, quote=True)}\"></iframe>"
            "</div>\n"
        )


class VegaLiteBlock:
    language = "vega"

    def render(self, block: FencedCodeBlock) -> str | None:
        base = _backend_base_url()
        query = urlencode({"b64": _encode_code_b64(block.code)})
        iframe_src = f"{base}/__embed/vega?{query}"
        return (
            "\n<div class=\"my-4 w-full\">"
            "<iframe sandbox=\"allow-scripts allow-same-origin\" "
            "style=\"width:100%;height:520px;border:0;\" "
            f"src=\"{html.escape(iframe_src, quote=True)}\"></iframe>"
            "</div>\n"
        )


EMBED_EXTENSIONS: dict[str, EmbedExtension] = {
    "youtube": YouTubeEmbed(),
    "vimeo": VimeoEmbed(),
    "gist": GistEmbed(),
    "slideshare": SlideShareEmbed(),
    "speakerdeck": SpeakerDeckEmbed(),
    "pdf": PdfEmbed(),
}


FENCED_BLOCK_EXTENSIONS: dict[str, FencedBlockExtension] = {
    "sequence": SequenceDiagramBlock(),
    "flow": FlowChartBlock(),
    "flowchart": FlowChartBlock(),
    "graphviz": GraphvizBlock(),
    "dot": GraphvizBlock(),
    "mermaid": MermaidBlock(),
    "abc": AbcBlock(),
    "vega": VegaLiteBlock(),
    "vega-lite": VegaLiteBlock(),
}


def apply_hackmd_embeds(markdown_text: str, *, extensions: dict[str, EmbedExtension] | None = None) -> str:
    """Convert HackMD-like extensions into raw HTML blocks.

    Unknown directives are left unchanged.

    Args:
        markdown_text: Source markdown.
        extensions: Optional mapping overriding EMBED_EXTENSIONS.
    """

    directive_registry = extensions or EMBED_EXTENSIONS
    text = markdown_text or ""

    def _replace_directives(segment: str) -> str:
        def _replace(match: re.Match) -> str:
            raw = match.group(0)
            name = (match.group("name") or "").strip().lower()
            args = (match.group("args") or "").strip()
            ext = directive_registry.get(name)
            if not ext:
                return raw

            rendered = ext.render(EmbedDirective(name=name, args=args, raw=raw))
            return rendered if rendered is not None else raw

        return _DIRECTIVE_RE.sub(_replace, segment)

    out_parts: list[str] = []

    fence_open_re = re.compile(r"^(?P<indent>\s{0,3})(?P<fence>`{3,}|~{3,})(?P<info>.*)$")
    lines = text.splitlines(keepends=True)
    i = 0
    buf: list[str] = []

    def _flush_buf():
        if not buf:
            return
        out_parts.append(_replace_directives("".join(buf)))
        buf.clear()

    while i < len(lines):
        line = lines[i].rstrip("\r\n")
        m_open = fence_open_re.match(line)
        if not m_open:
            buf.append(lines[i])
            i += 1
            continue

        _flush_buf()

        indent = m_open.group("indent")
        fence = m_open.group("fence")
        info = (m_open.group("info") or "").strip()
        fence_char = fence[0]
        fence_len = len(fence)
        close_re = re.compile(rf"^{re.escape(indent)}{re.escape(fence_char)}{{{fence_len},}}\s*$")

        j = i + 1
        body_lines: list[str] = []
        while j < len(lines) and not close_re.match(lines[j].rstrip("\r\n")):
            body_lines.append(lines[j])
            j += 1

        if j >= len(lines):
            # Unclosed fence: treat as literal text.
            buf.append(lines[i])
            buf.extend(body_lines)
            break

        raw = "".join([lines[i], *body_lines, lines[j]])

        token = (info.split(None, 1)[0] if info else "").strip()
        # HackMD-style options live on the first token: lang=101, lang=+, lang!
        if token.endswith("!"):
            token = token[:-1]
        if "=" in token:
            token = token.split("=", 1)[0]
        lang = token.strip().lower()

        code = "".join(body_lines)
        # Match old behavior: fenced body excludes the newline right before the closing fence.
        if code.endswith("\n"):
            code = code[:-1]
            if code.endswith("\r"):
                code = code[:-1]

        block_ext = FENCED_BLOCK_EXTENSIONS.get(lang)
        if block_ext:
            rendered = block_ext.render(FencedCodeBlock(language=lang, code=code, raw=raw))
            out_parts.append(rendered if rendered is not None else raw)
        else:
            out_parts.append(raw)

        i = j + 1

    _flush_buf()
    return "".join(out_parts)
