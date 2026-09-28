"""Link-preview (Open Graph) endpoints for shared documents.

The frontend `/doc/<id>` route is a static SPA shell, so crawlers that don't run
JavaScript (chat apps building URL previews) only ever see generic metadata.
These backend routes expose per-document Open Graph tags instead:

- ``/__og/doc/{doc_id}``           HTML with og:* meta; humans get redirected to the doc.
- ``/__og/doc/{doc_id}/image.svg`` A simple title card used as og:image.
"""

from __future__ import annotations

import html
import re

from starlette.requests import Request
from starlette.responses import HTMLResponse, Response

from codoc_in_md.state import DOCUMENTS_STORE

SITE_NAME = "CoDoc in MD"
_DESCRIPTION_LIMIT = 200


def _public_base_url(request: Request) -> str:
    """Public origin as seen by the client (honours reverse-proxy headers)."""
    proto = request.headers.get("x-forwarded-proto") or request.url.scheme
    host = request.headers.get("x-forwarded-host") or request.headers.get("host") or request.url.netloc
    return f"{proto.split(',')[0].strip()}://{host.split(',')[0].strip()}"


def _plain_description(content: str, title: str) -> str:
    """Turn the markdown body into a short plain-text summary."""
    text = re.sub(r"```.*?```", " ", content or "", flags=re.S)
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        heading = re.match(r"^#{1,6}\s+(.*)", stripped)
        if heading and heading.group(1).strip() == title:
            continue
        lines.append(stripped)
    text = " ".join(lines)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)  # images
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)  # links -> label
    text = re.sub(r"<[^>]+>", " ", text)  # inline html
    text = re.sub(r"^[#>\-*+]+\s*|[*_`~]+|\{%.*?%\}", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > _DESCRIPTION_LIMIT:
        text = text[: _DESCRIPTION_LIMIT - 1].rstrip() + "…"
    return text


def _svg_card(title: str, author: str) -> str:
    # Rough wrapping; SVG has no native text wrap.
    words = list(title) if re.search(r"[　-鿿]", title) else title.split(" ")
    joiner = "" if re.search(r"[　-鿿]", title) else " "
    max_units = 18 if joiner == "" else 32
    rows: list[str] = []
    current = ""
    for w in words:
        candidate = f"{current}{joiner}{w}" if current else w
        if len(candidate) > max_units and current:
            rows.append(current)
            current = w
        else:
            current = candidate
    if current:
        rows.append(current)
    if len(rows) > 3:
        rows = rows[:3]
        rows[-1] = rows[-1][:-1] + "…"

    tspans = "".join(
        f'<tspan x="64" dy="{0 if i == 0 else 64}">{html.escape(r)}</tspan>' for i, r in enumerate(rows)
    )
    author_line = f"by {html.escape(author)}" if author else ""
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630">'
        '<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
        '<stop offset="0" stop-color="#7c3aed"/><stop offset="1" stop-color="#4f46e5"/>'
        "</linearGradient></defs>"
        '<rect width="1200" height="630" fill="url(#g)"/>'
        '<rect x="40" y="40" width="1120" height="550" rx="28" fill="#ffffff"/>'
        '<text x="64" y="120" font-family="Raleway, Helvetica, Arial, sans-serif" font-size="30" '
        f'font-weight="600" fill="#7c3aed">📝 {SITE_NAME}</text>'
        '<text x="64" y="250" font-family="Raleway, Helvetica, Arial, \'PingFang TC\', \'Noto Sans CJK TC\', sans-serif" '
        f'font-size="54" font-weight="700" fill="#111827">{tspans}</text>'
        '<text x="64" y="545" font-family="Raleway, Helvetica, Arial, sans-serif" font-size="28" '
        f'fill="#6b7280">{author_line}</text>'
        "</svg>"
    )


def register_link_preview_routes(app) -> None:
    """Register Open Graph preview routes on the Reflex backend."""

    def _api_og_doc(request: Request) -> Response:
        doc_id = request.path_params["doc_id"]
        base = _public_base_url(request)
        doc_url = f"{base}/doc/{doc_id}"
        doc = DOCUMENTS_STORE.get(doc_id)
        if doc is None:
            title, description, author = "Untitled", "Collaborative Markdown document", ""
        else:
            title = doc.get("title") or "Untitled"
            author = doc.get("created_by_name") or ""
            description = _plain_description(doc.get("content", ""), title) or "Collaborative Markdown document"

        e = html.escape
        meta = {
            "og:type": "article",
            "og:site_name": SITE_NAME,
            "og:title": title,
            "og:description": description,
            "og:url": doc_url,
            "og:image": f"{base}/__og/doc/{doc_id}/image.svg",
        }
        tags = "".join(f'<meta property="{k}" content="{e(v)}"/>' for k, v in meta.items())
        if author:
            tags += f'<meta name="author" content="{e(author)}"/>'
        body = (
            "<!doctype html><html><head><meta charset='utf-8'/>"
            f"<title>{e(title)} | {SITE_NAME}</title>"
            f'<meta name="description" content="{e(description)}"/>'
            f'<meta name="twitter:card" content="summary_large_image"/>{tags}'
            f'<link rel="canonical" href="{e(doc_url)}"/>'
            f'<meta http-equiv="refresh" content="0; url={e(doc_url)}"/>'
            f'</head><body><a href="{e(doc_url)}">{e(title)}</a></body></html>'
        )
        return HTMLResponse(body, headers={"Cache-Control": "public, max-age=60"})

    def _api_og_doc_image(request: Request) -> Response:
        doc = DOCUMENTS_STORE.get(request.path_params["doc_id"])
        title = (doc or {}).get("title") or "Untitled"
        author = (doc or {}).get("created_by_name") or ""
        return Response(
            _svg_card(title, author),
            media_type="image/svg+xml",
            headers={"Cache-Control": "public, max-age=60"},
        )

    existing = {getattr(r, "path", None) for r in getattr(app._api, "routes", [])}
    if "/__og/doc/{doc_id}" not in existing:
        app._api.add_route("/__og/doc/{doc_id}", _api_og_doc, methods=["GET"])
        app._api.add_route("/__og/doc/{doc_id}/image.svg", _api_og_doc_image, methods=["GET"])
