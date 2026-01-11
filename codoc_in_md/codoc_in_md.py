import reflex as rx
from reflex_monaco import monaco
from codoc_in_md.state import EditorState
from codoc_in_md.components.header import header
from codoc_in_md.components.sidebar import sidebar
from codoc_in_md.components.markdown_clean import CleanMarkdown

from codoc_in_md.embeds import register_backend_embed_routes


def editor_panel() -> rx.Component:
    """The raw Monaco editor panel."""
    return rx.el.div(
        monaco(
            value=EditorState.doc_content,
            language="markdown",
            theme="vs-light",
            on_change=EditorState.update_content,
            options={
                "wordWrap": "on",
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

    def _children_node(node):
        """Return the rendered children payload for rx.markdown component_map."""

        if node is None:
            return ""
        if isinstance(node, dict):
            return node.get("children")
        return node

    def _as_fragment(children):
        if isinstance(children, list):
            return rx.fragment(*children)
        return rx.fragment(children)

    return rx.el.div(
        CleanMarkdown.create(
            EditorState.doc_content_rendered,
            component_map={
                "h1": lambda node: rx.el.h1(
                    _as_fragment(_children_node(node)),
                    class_name="text-3xl font-bold text-gray-900 mb-4",
                ),
                "h2": lambda node: rx.el.h2(
                    _as_fragment(_children_node(node)),
                    class_name="text-2xl font-bold text-gray-800 mt-6 mb-3 pb-1 border-b",
                ),
                "h3": lambda node: rx.el.h3(
                    _as_fragment(_children_node(node)),
                    class_name="text-xl font-bold text-gray-800 mt-4 mb-2",
                ),
                "p": lambda node: rx.el.p(
                    _as_fragment(_children_node(node)),
                    class_name="mb-4 text-gray-700 leading-relaxed whitespace-pre-wrap",
                ),
                "ul": lambda node: rx.el.ul(
                    _as_fragment(_children_node(node)),
                    class_name="list-disc list-inside mb-4 pl-4",
                ),
                "ol": lambda node: rx.el.ol(
                    _as_fragment(_children_node(node)),
                    class_name="list-decimal list-inside mb-4 pl-4",
                ),
                "li": lambda node: rx.el.li(
                    _as_fragment(_children_node(node)),
                    class_name="mb-1 text-gray-700 whitespace-pre-wrap",
                ),
                "blockquote": lambda node: rx.el.blockquote(
                    _as_fragment(_children_node(node)),
                    class_name="border-l-4 border-gray-300 pl-4 italic my-4",
                ),
                "table": lambda node: rx.el.div(
                    rx.el.div(
                        rx.el.table(
                            _as_fragment(_children_node(node)),
                            class_name="min-w-full border-collapse text-sm text-gray-800",
                        ),
                        class_name="overflow-x-auto",
                    ),
                    class_name="my-6 rounded-lg border border-gray-200 bg-white overflow-hidden",
                ),
                "thead": lambda node: rx.el.thead(
                    _as_fragment(_children_node(node)),
                    class_name="bg-gray-50 border-b border-gray-200",
                ),
                "tbody": lambda node: rx.el.tbody(
                    _as_fragment(_children_node(node)),
                    class_name="bg-white",
                ),
                "tr": lambda node: rx.el.tr(
                    _as_fragment(_children_node(node)),
                    class_name="border-b border-gray-200 last:border-b-0 even:bg-gray-50/40",
                ),
                "th": lambda node: rx.el.th(
                    _as_fragment(_children_node(node)),
                    class_name="px-4 py-3 text-xs font-semibold text-gray-700 border-r border-gray-200 last:border-r-0 whitespace-nowrap",
                ),
                "td": lambda node: rx.el.td(
                    _as_fragment(_children_node(node)),
                    class_name="px-4 py-3 align-top border-r border-gray-200 last:border-r-0 whitespace-normal break-words",
                ),
            },
        ),
        class_name="h-full w-full p-8 overflow-auto bg-white",
    )


def content_area() -> rx.Component:
    """The main content area handling editor, preview, and split views."""
    return rx.el.div(
        rx.cond(
            EditorState.view_mode != "preview",
            rx.el.div(
                editor_panel(),
                class_name=rx.cond(
                    EditorState.view_mode == "split",
                    "w-1/2 h-full border-r border-gray-200",
                    "w-full h-full",
                ),
            ),
        ),
        rx.cond(
            EditorState.view_mode != "editor",
            rx.el.div(
                preview_panel(),
                class_name=rx.cond(
                    EditorState.view_mode == "split",
                    "w-1/2 h-full bg-gray-50",
                    "w-full h-full bg-gray-50 mx-auto max-w-4xl border-l border-gray-100 shadow-sm",
                ),
            ),
        ),
        class_name="flex flex-1 overflow-hidden h-full w-full relative",
    )


def index() -> rx.Component:
    """The main page of the collaborative editor."""
    return rx.el.main(
        rx.el.div(
            header(),
            rx.el.div(
                sidebar(), content_area(), class_name="flex flex-1 overflow-hidden"
            ),
            class_name="flex flex-col h-screen w-full bg-white",
        ),
        class_name="font-['Raleway']",
    )


app = rx.App(
    theme=rx.theme(appearance="light"),
    head_components=[
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