"""HackMD-like embed directive processing.

This module provides a small, extensible architecture to translate directives like:
  {%youtube OPqDaOsYo-U %}
into raw HTML blocks suitable for rendering inside rx.markdown.

Add new embed types by registering an implementation in EMBED_EXTENSIONS.
"""

from __future__ import annotations

from dataclasses import dataclass
import html
import re
from typing import Protocol
from urllib.parse import parse_qs, urlparse


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

        # Expect a full gist URL, or a direct .js embed URL.
        gist_js_url: str | None = None
        if value.lower().startswith("https://"):
            gist_js_url = value
        else:
            return None

        # Render via iframe+srcdoc so the gist's embed script can execute.
        srcdoc = (
            "<!doctype html><html><head><meta charset='utf-8'/>"
            "<style>body{margin:0;padding:0} .gist{font-size:12px}</style>"
            "</head><body>"
            f"<script src='{_escape_attr(gist_js_url)}'></script>"
            "</body></html>"
        )
        return (
            "\n<div class=\"my-4 w-full\">"
            "<iframe sandbox=\"allow-scripts allow-same-origin\" "
            "style=\"width:100%;height:420px;border:0;\" "
            f"srcdoc=\"{_escape_attr(srcdoc)}\"></iframe>"
            "</div>\n"
        )


class SequenceDiagramBlock:
    language = "sequence"

    def render(self, block: FencedCodeBlock) -> str | None:
        source_html = html.escape(block.code)
        srcdoc = (
            "<!doctype html><html><head><meta charset='utf-8'/>"
            "<meta name='viewport' content='width=device-width, initial-scale=1'/>"
            "<style>body{margin:0;padding:12px;font-family:sans-serif} #diagram{width:100%}</style>"
            "<script src='https://bramp.github.io/js-sequence-diagrams/js/webfont.js'></script>"
            "<script src='https://bramp.github.io/js-sequence-diagrams/js/snap.svg-min.js'></script>"
            "<script src='https://bramp.github.io/js-sequence-diagrams/js/underscore-min.js'></script>"
            "<script src='https://bramp.github.io/js-sequence-diagrams/js/sequence-diagram-min.js'></script>"
            "</head><body>"
            f"<pre id='source' style='display:none'>{source_html}</pre>"
            "<div id='diagram'></div>"
            "<script>(function(){try{var text=document.getElementById('source').textContent;"
            "var d=Diagram.parse(text);d.drawSVG('diagram',{theme:'simple'});}catch(e){"
            "var pre=document.createElement('pre');pre.textContent=text;document.body.appendChild(pre);}})();</script>"
            "</body></html>"
        )

        return (
            "\n<div class=\"my-4 w-full\">"
            "<iframe sandbox=\"allow-scripts allow-same-origin\" "
            "style=\"width:100%;height:360px;border:0;\" "
            f"srcdoc=\"{_escape_attr(srcdoc)}\"></iframe>"
            "</div>\n"
        )


EMBED_EXTENSIONS: dict[str, EmbedExtension] = {
    "youtube": YouTubeEmbed(),
    "vimeo": VimeoEmbed(),
    "gist": GistEmbed(),
    "slideshare": GenericIFrameEmbed("slideshare", title="SlideShare", height_px=520),
    "speakerdeck": GenericIFrameEmbed("speakerdeck", title="SpeakerDeck", height_px=520),
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
