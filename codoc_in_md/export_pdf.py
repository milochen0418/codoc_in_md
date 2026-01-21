from __future__ import annotations

import re
from pathlib import Path

from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response

from .state import DOCUMENTS_STORE, render_markdown_for_export


_PDF_CSS = """
@page {
  size: A4;
  margin: 12mm;
}

* {
  box-sizing: border-box;
}

html, body {
  color: #111827;
  font-family: "Raleway", "Helvetica Neue", Arial, sans-serif;
  font-size: 12pt;
  line-height: 1.6;
}

h1 {
  font-size: 24pt;
  margin: 0 0 12pt;
  border-bottom: 1px solid #e5e7eb;
  padding-bottom: 6pt;
}

h2 {
  font-size: 18pt;
  margin: 18pt 0 10pt;
  border-bottom: 1px solid #e5e7eb;
  padding-bottom: 4pt;
}

h3 {
  font-size: 15pt;
  margin: 14pt 0 8pt;
}

p {
  margin: 0 0 10pt;
  white-space: pre-wrap;
}

ul, ol {
  margin: 0 0 10pt 18pt;
}

blockquote {
  margin: 10pt 0;
  padding-left: 12pt;
  border-left: 4px solid #d1d5db;
  color: #374151;
}

table {
  width: 100%;
  border-collapse: collapse;
  margin: 12pt 0;
  font-size: 10.5pt;
}

table th,
 table td {
  border: 1px solid #e5e7eb;
  padding: 6pt 8pt;
  vertical-align: top;
}

table thead th {
  background: #f3f4f6;
}

pre {
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  padding: 8pt;
  font-size: 9.5pt;
  overflow-wrap: break-word;
}

code {
  font-family: "SFMono-Regular", Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
  font-size: 9.5pt;
  background: #e5f0ff;
  color: #0f172a;
  padding: 1pt 3pt;
  border-radius: 4pt;
}

mark {
  background: #dbeafe;
  color: #0f172a;
  padding: 0 2pt;
}

a {
  color: #2563eb;
  text-decoration: underline;
}

img {
  max-width: 100%;
  height: auto;
}

.codoc-mdline,
[data-codoc-tail],
.codoc-toc {
  display: none !important;
}
"""


def register_pdf_export_routes(app) -> None:
    """Register PDF export endpoint on the backend (port 8000)."""

    def _extract_title(markdown_text: str, fallback: str) -> str:
        for line in (markdown_text or "").splitlines():
            m = re.match(r"^\s*#\s+(.+?)\s*$", line)
            if m:
                title = m.group(1).strip()
                if title:
                    return title
        return fallback

    def _sanitize_filename(value: str) -> str:
        name = re.sub(r"[\\/:*?\"<>|]+", "-", value).strip()
        name = re.sub(r"\s+", " ", name)
        return name or "document"

    def _render_html(markdown_text: str, base_url: str) -> str:
        try:
            import markdown as md
        except Exception as exc:
            raise RuntimeError("Missing python-markdown dependency") from exc

        rendered = md.markdown(
            markdown_text,
            extensions=[
                "tables",
                "fenced_code",
                "sane_lists",
                "attr_list",
            ],
            output_format="html5",
        )

        base = base_url.rstrip("/")
        rendered = re.sub(r"src=\"/", f'src="{base}/', rendered)
        rendered = re.sub(r"href=\"/", f'href="{base}/', rendered)

        return (
            "<!doctype html><html><head><meta charset=\"utf-8\"/>"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"/>"
            "</head><body>"
            f"<article class=\"markdown-body\">{rendered}</article>"
            "</body></html>"
        )

    def _api_export_pdf(request: Request) -> Response:
        doc_id = (request.query_params.get("doc_id") or "").strip()
        if not doc_id:
            return PlainTextResponse("Missing doc_id", status_code=400)

        doc = DOCUMENTS_STORE.get(doc_id)
        if not doc:
            return PlainTextResponse("Document not found", status_code=404)

        raw_content = doc.get("content") or ""
        prepared = render_markdown_for_export(raw_content)
        title = _extract_title(raw_content, doc_id)

        try:
            html = _render_html(prepared, str(request.base_url))
        except RuntimeError as exc:
            return PlainTextResponse(str(exc), status_code=500)

        try:
            from weasyprint import CSS, HTML
        except Exception:
            return PlainTextResponse("Missing WeasyPrint dependency", status_code=500)

        base_path = str(Path(__file__).resolve().parents[1])
        pdf_bytes = HTML(string=html, base_url=base_path).write_pdf(
            stylesheets=[CSS(string=_PDF_CSS)]
        )

        filename = _sanitize_filename(title)
        headers = {
            "Content-Disposition": f'attachment; filename="{filename}.pdf"'
        }
        return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)

    existing_paths = {getattr(r, "path", None) for r in getattr(app._api, "routes", [])}
    if "/__export/pdf" not in existing_paths:
        app._api.add_route("/__export/pdf", _api_export_pdf, methods=["GET"])
