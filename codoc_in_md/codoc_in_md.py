import os
import reflex as rx
from reflex_monaco import monaco
from codoc_in_md.state import EditorState
from codoc_in_md.components.header import header
from codoc_in_md.components.sidebar import sidebar
from codoc_in_md.components.markdown_clean import CleanMarkdown

from codoc_in_md.embeds import register_backend_embed_routes
from codoc_in_md.export_pdf import register_pdf_export_routes


def editor_panel() -> rx.Component:
    """The raw Monaco editor panel."""
    return rx.el.div(
        monaco(
            key=EditorState.editor_component_key,
            default_value=EditorState.editor_seed_content,
            language="markdown",
            theme="vs-light",
            on_change=EditorState.update_content,
            options={
                "wordWrap": "on",
                "scrollBeyondLastLine": True,
                "minimap": {"enabled": False},
                "lineNumbers": "off",
                "glyphMargin": False,
                "folding": False,
                "lineDecorationsWidth": 0,
                "lineNumbersMinChars": 0,
            },
            height="100%",
            width="100%",
        ),
        class_name="h-full w-full",
    )


def preview_panel() -> rx.Component:
    """The markdown preview panel."""

    def _as_fragment(*children):
        # `CleanMarkdown` passes react-markdown children as a runtime Var.
        # Wrap in a fragment so we can add our own wrapper elements/styles.
        if len(children) == 1 and isinstance(children[0], list):
            return rx.fragment(*children[0])
        return rx.fragment(*children)

    def _safe_dom_props(props: dict) -> dict:
        # Preserve useful DOM attributes (especially `id` for heading anchors/TOC)
        # while avoiding react-markdown internal props that cause warnings.
        out: dict = {}
        for key, val in (props or {}).items():
            if key in {"id", "title", "lang", "dir", "style"}:
                out[key] = val
            elif isinstance(key, str) and (
                key.startswith("data-")
                or key.startswith("aria-")
                or key in {"data", "aria"}
            ):
                out[key] = val
        return out

    rendered = CleanMarkdown.create(
        EditorState.doc_content_rendered,
        component_map={
            "h1": lambda *children, **props: rx.el.h1(
                _as_fragment(*children),
                class_name="text-3xl font-bold text-gray-900 mb-4 pb-2 border-b border-gray-200",
                **_safe_dom_props(props),
            ),
            "h2": lambda *children, **props: rx.el.h2(
                _as_fragment(*children),
                class_name="text-2xl font-bold text-gray-800 mt-6 mb-3 pb-1 border-b",
                **_safe_dom_props(props),
            ),
            "h3": lambda *children, **props: rx.el.h3(
                _as_fragment(*children),
                class_name="text-xl font-bold text-gray-800 mt-4 mb-2",
                **_safe_dom_props(props),
            ),
            "p": lambda *children, **props: rx.el.p(
                _as_fragment(*children),
                class_name="mb-4 text-gray-700 leading-relaxed whitespace-pre-wrap",
                **_safe_dom_props(props),
            ),
            "ul": lambda *children, **props: rx.el.ul(
                _as_fragment(*children),
                class_name="list-disc list-inside mb-4 pl-4",
                **_safe_dom_props(props),
            ),
            "ol": lambda *children, **props: rx.el.ol(
                _as_fragment(*children),
                class_name="list-decimal list-inside mb-4 pl-4",
                **_safe_dom_props(props),
            ),
            "li": lambda *children, **props: rx.el.li(
                _as_fragment(*children),
                class_name="mb-1 text-gray-700 whitespace-pre-wrap",
                **_safe_dom_props(props),
            ),
            "blockquote": lambda *children, **props: rx.el.blockquote(
                _as_fragment(*children),
                class_name="border-l-4 border-gray-300 pl-4 italic my-4",
                **_safe_dom_props(props),
            ),
            "table": lambda *children, **props: rx.el.div(
                rx.el.div(
                    rx.el.table(
                        _as_fragment(*children),
                        class_name="min-w-full border-collapse text-sm text-gray-800",
                    ),
                    class_name="overflow-x-auto",
                ),
                class_name="my-6 rounded-lg border border-gray-200 bg-white overflow-hidden",
                **_safe_dom_props(props),
            ),
            "thead": lambda *children, **props: rx.el.thead(
                _as_fragment(*children),
                class_name="bg-gray-50 border-b border-gray-200",
                **_safe_dom_props(props),
            ),
            "tbody": lambda *children, **props: rx.el.tbody(
                _as_fragment(*children),
                class_name="bg-white",
                **_safe_dom_props(props),
            ),
            "tr": lambda *children, **props: rx.el.tr(
                _as_fragment(*children),
                class_name="border-b border-gray-200 last:border-b-0 even:bg-gray-50/40",
                **_safe_dom_props(props),
            ),
            "th": lambda *children, **props: rx.el.th(
                _as_fragment(*children),
                class_name="px-4 py-3 text-xs font-semibold text-gray-700 border-r border-gray-200 last:border-r-0 whitespace-nowrap",
                **_safe_dom_props(props),
            ),
            "td": lambda *children, **props: rx.el.td(
                _as_fragment(*children),
                class_name="px-4 py-3 align-top border-r border-gray-200 last:border-r-0 whitespace-normal break-words",
                **_safe_dom_props(props),
            ),
        },
    )

    # IMPORTANT: make the scroll container full-width so the vertical scrollbar
    # is at the far right (HackMD-like), while keeping the content readable via
    # an inner max-width wrapper.
    return rx.el.div(
        rx.el.div(
            rendered,
            class_name="min-h-full w-full max-w-4xl mx-auto p-8 bg-white",
        ),
        id="preview-pane",
        class_name="h-full w-full overflow-y-auto overflow-x-hidden bg-gray-50",
    )


def split_divider() -> rx.Component:
        """The draggable split divider with a scroll-lock toggle."""

        lock_icon = rx.cond(
                EditorState.is_scroll_locked,
                rx.icon("lock", class_name="h-4 w-4"),
        rx.icon("lock_open", class_name="h-4 w-4"),
        )

        return rx.el.div(
                rx.el.button(
                        lock_icon,
                        on_click=EditorState.toggle_scroll_lock,
                        title=rx.cond(
                                EditorState.is_scroll_locked,
                                "Scroll locked (preview follows editor)",
                                "Scroll unlocked (scroll independently)",
                        ),
                        class_name="p-1 rounded hover:bg-gray-100 text-gray-600",
                ),
                id="split-divider",
                class_name="h-full w-3 bg-gray-200 hover:bg-gray-300 cursor-col-resize flex items-center justify-center select-none",
        )


def split_interactions_script() -> rx.Component:
        """Deprecated: client interactions are loaded via assets/codoc_split.js."""

        return rx.fragment()


def content_area() -> rx.Component:
    """The main content area handling editor, preview, and split views."""
    return rx.el.div(
        rx.cond(
            EditorState.view_mode == "split",
            rx.el.div(
                rx.el.div(
                    editor_panel(),
                    id="editor-pane",
                    class_name="h-full w-full overflow-hidden min-h-0 min-w-0",
                ),
                split_divider(),
                rx.el.div(
                    preview_panel(),
                    class_name="h-full w-full min-h-0 min-w-0 overflow-hidden",
                ),
                # data_locked is read by the injected JS (supports both data-locked and data_locked).
                id="codoc-split",
                data_locked=EditorState.is_scroll_locked,
                style={"gridTemplateColumns": "var(--codoc-split-left, 50%) 12px 1fr"},
                class_name="grid flex-1 overflow-hidden h-full w-full relative min-h-0",
            ),
            rx.el.div(
                rx.cond(
                    EditorState.view_mode != "preview",
                    rx.el.div(editor_panel(), id="editor-pane", class_name="w-full h-full"),
                ),
                rx.cond(
                    EditorState.view_mode != "editor",
                    rx.el.div(
                        preview_panel(),
                        class_name="w-full h-full overflow-hidden",
                    ),
                ),
                class_name="flex flex-1 overflow-hidden h-full w-full relative min-h-0",
            ),
        ),
        class_name="flex flex-1 overflow-hidden h-full w-full relative min-h-0",
    )


def index() -> rx.Component:
    """The main page of the collaborative editor."""
    return rx.el.main(
        rx.el.div(
            header(),
            rx.el.div(
                sidebar(), content_area(), class_name="flex flex-1 overflow-hidden min-h-0"
            ),
            class_name="flex flex-col h-screen w-full bg-white",
        ),
        class_name="font-['Raleway']",
    )


app = rx.App(
    theme=rx.theme(appearance="light"),
    head_components=[
        rx.el.script(
            f"window.CODOC_BACKEND_BASE_URL = '{os.getenv('CODOC_BACKEND_BASE_URL', 'http://localhost:8000').rstrip('/')}'"
        ),
        rx.el.script(src="/codoc_split.js", defer=True),
        rx.el.script(src="/fontawesome_fix.js", defer=True),
        rx.el.script(src="/fullscreen.js", defer=True),
        rx.el.script(src="/export_pdf.js", defer=True),
        # HackMD commonly uses Font Awesome 4 markup like: <i class="fa fa-...">.
        # Load FA so those icons render in the preview.
        rx.el.link(
            rel="stylesheet",
            href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.7.0/css/font-awesome.min.css",
        ),
        rx.el.link(rel="stylesheet", href="/fullscreen.css"),
        rx.el.link(rel="stylesheet", href="/print.css"),
        rx.el.link(rel="preconnect", href="https://fonts.googleapis.com"),
        rx.el.link(rel="preconnect", href="https://fonts.gstatic.com", crossorigin=""),
        rx.el.link(
            href="https://fonts.googleapis.com/css2?family=Raleway:wght@400;500;600;700&display=swap",
            rel="stylesheet",
        ),
    ],
)
app.add_page(index, route="/doc/[document_id]", on_load=EditorState.on_load)
app.add_page(index, route="/", on_load=EditorState.on_load)

# Backend embed endpoints (used by fenced-block renderers like ```sequence```).
register_backend_embed_routes(app)
# PDF export endpoint (HackMD/CodiMD-like server-side export).
register_pdf_export_routes(app)