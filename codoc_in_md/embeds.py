"""HackMD-like embed directive processing.

This module provides a small, extensible architecture to translate directives like:
  {%youtube OPqDaOsYo-U %}
into raw HTML blocks suitable for rendering inside rx.markdown.

Add new embed types by registering an implementation in EMBED_EXTENSIONS.
"""

from __future__ import annotations

from dataclasses import dataclass
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
from starlette.responses import HTMLResponse


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
    r"```(?P<lang>[A-Za-z0-9_-]+)?[ \t]*\r?\n(?P<body>.*?)(?:\r?\n)```",
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

        safe_url = html.escape(url, quote=True)
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
        code = (request.query_params.get("code") or "").strip()
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

    existing_paths = {getattr(r, "path", None) for r in getattr(app._api, "routes", [])}
    if "/__embed/gist" not in existing_paths:
        app._api.add_route("/__embed/gist", _api_embed_gist, methods=["GET"])
    if "/__embed/sequence" not in existing_paths:
        app._api.add_route("/__embed/sequence", _api_embed_sequence, methods=["GET"])


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
        query = urlencode({"code": block.code})
        iframe_src = f"{base}/__embed/sequence?{query}"
        return (
            "\n<div class=\"my-4 w-full\">"
            "<iframe sandbox=\"allow-scripts allow-same-origin\" "
            "style=\"width:100%;height:360px;border:0;\" "
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
        lang = (match.group("lang") or "").strip().lower()
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
