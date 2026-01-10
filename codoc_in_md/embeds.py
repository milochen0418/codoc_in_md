"""HackMD-like embed directive processing.

This module provides a small, extensible architecture to translate directives like:
  {%youtube OPqDaOsYo-U %}
into raw HTML blocks suitable for rendering inside rx.markdown.

Add new embed types by registering an implementation in EMBED_EXTENSIONS.
"""

from __future__ import annotations

from dataclasses import dataclass
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


_DIRECTIVE_RE = re.compile(
    r"\{\%\s*(?P<name>[A-Za-z0-9_-]+)(?:\s+(?P<args>.*?))?\s*\%\}",
    re.IGNORECASE | re.DOTALL,
)


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


EMBED_EXTENSIONS: dict[str, EmbedExtension] = {
    "youtube": YouTubeEmbed(),
}


def apply_hackmd_embeds(markdown_text: str, *, extensions: dict[str, EmbedExtension] | None = None) -> str:
    """Convert HackMD-like embed directives into raw HTML blocks.

    Unknown directives are left unchanged.

    Args:
        markdown_text: Source markdown.
        extensions: Optional mapping overriding EMBED_EXTENSIONS.
    """

    registry = extensions or EMBED_EXTENSIONS

    def _replace(match: re.Match) -> str:
        raw = match.group(0)
        name = (match.group("name") or "").strip().lower()
        args = (match.group("args") or "").strip()
        ext = registry.get(name)
        if not ext:
            return raw

        rendered = ext.render(EmbedDirective(name=name, args=args, raw=raw))
        return rendered if rendered is not None else raw

    return _DIRECTIVE_RE.sub(_replace, markdown_text or "")
