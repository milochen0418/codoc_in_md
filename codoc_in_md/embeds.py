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


_DIRECTIVE_RE = re.compile(
    r"\{\%\s*(?P<name>[A-Za-z0-9_-]+)(?:\s+(?P<args>.*?))?\s*\%\}",
    re.IGNORECASE | re.DOTALL,
)

_FENCED_BLOCK_RE = re.compile(
    r"```(?P<info>[^\n]*)\r?\n(?P<body>.*?)(?:\r?\n)```",
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
    last = 0

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

        # Apply typography to each non-directive chunk, preserving inline code.
        for i, chunk in enumerate(parts):
            if i % 2 == 1:
                out_parts.append(chunk)
                continue

            # Split on inline code spans (backticks) and only transform non-code.
            buf = chunk
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

    for match in _FENCED_BLOCK_RE.finditer(text):
        _process_noncode(text[last : match.start()])
        out_parts.append(match.group(0))
        last = match.end()
    _process_noncode(text[last:])

    return "".join(out_parts)


_CODE_FENCE_RE = re.compile(
    r"```(?P<info>[^\n]*)\r?\n(?P<body>.*?)(?:\r?\n)```",
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

    def _line_count(body: str) -> int:
        if body is None:
            return 0
        # markdown fences capture body without the trailing newline before closing ```.
        if body == "":
            return 0
        return body.count("\n") + 1

    def _rewrite(match: re.Match) -> str:
        nonlocal last_end_line
        info = (match.group("info") or "").rstrip("\r")
        body = match.group("body") or ""

        stripped = info.strip()
        if not stripped:
            return match.group(0)

        # Only rewrite the first token; keep the rest intact.
        parts = stripped.split(None, 1)
        token = parts[0]
        rest = parts[1] if len(parts) > 1 else ""

        wrap = False
        if token.endswith("!"):
            wrap = True
            token = token[:-1]

        # Handle `!` with no language by forcing a safe base language.
        if wrap and not token:
            token = "markdown"

        if "=" in token:
            lang, _, spec = token.partition("=")
            spec = spec.strip()

            start: int | None
            if spec == "+":
                start = (last_end_line + 1) if last_end_line is not None else 1
            elif spec == "":
                start = 1
            elif spec.isdigit():
                start = int(spec)
            else:
                start = None

            if start is not None:
                cnt = _line_count(body)
                last_end_line = start + max(cnt - 1, 0)
                # Encode options into a parser-friendly token.
                base = (lang or "markdown")
                token = f"{base}-linenos-{start}"
            else:
                # Unknown spec: keep original token.
                token = parts[0]

        if wrap and token and not token.endswith("-wrap"):
            token = token + "-wrap"

        new_info = (token + (" " + rest if rest else "")).rstrip()
        # Preserve original leading/trailing spaces on the info line.
        prefix = info[: len(info) - len(info.lstrip(" "))]
        suffix = info[len(info.rstrip(" ")) :]
        return f"```{prefix}{new_info}{suffix}\n{body}\n```"

    return _CODE_FENCE_RE.sub(_rewrite, text)


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

    fence_open_re = re.compile(r"^(?P<indent>\s{0,3})```(?P<info>.*?)(?:\r?\n)?$")

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
        m_open = fence_open_re.match(lines[i])
        if not m_open:
            out.append(lines[i])
            i += 1
            continue

        indent = m_open.group("indent")
        info = m_open.group("info") or ""
        j = i + 1
        body_lines: list[str] = []

        fence_close_re = re.compile(rf"^{re.escape(indent)}```\s*(?:\r?\n)?$")
        while j < len(lines) and not fence_close_re.match(lines[j]):
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
    last = 0
    for match in _FENCED_BLOCK_RE.finditer(text):
        # Apply directive replacements only in non-code segments.
        out_parts.append(_replace_directives(text[last : match.start()]))

        raw = match.group(0)
        info = (match.group("info") or "").strip()
        token = (info.split(None, 1)[0] if info else "").strip()
        # HackMD-style options live on the first token: lang=101, lang=+, lang!
        if token.endswith("!"):
            token = token[:-1]
        if "=" in token:
            token = token.split("=", 1)[0]
        lang = token.strip().lower()
        body = match.group("body") or ""
        block_ext = FENCED_BLOCK_EXTENSIONS.get(lang)
        if block_ext:
            rendered = block_ext.render(
                FencedCodeBlock(language=lang, code=body, raw=raw)
            )
            out_parts.append(rendered if rendered is not None else raw)
        else:
            out_parts.append(raw)

        last = match.end()

    out_parts.append(_replace_directives(text[last:]))
    return "".join(out_parts)
