import reflex as rx
from reflex_monaco import monaco
from codoc_in_md.state import EditorState
from codoc_in_md.components.header import header
from codoc_in_md.components.sidebar import sidebar

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

    def _children_to_text(children) -> str:
        if children is None:
            return ""
        if isinstance(children, str):
            return children
        if isinstance(children, list):
            return "".join(_children_to_text(c) for c in children)
        return ""

    def _markdown_pre(children):
        # We render fenced code blocks via `rx.code_block` in the `code` component,
        # so the surrounding <pre> from the markdown renderer should be removed.
        if isinstance(children, list):
            return rx.fragment(*children)
        return rx.fragment(children)

    def _markdown_code(node):
        # Reflex markdown may pass either a raw string (inline code) or a props dict.
        if isinstance(node, str):
            return rx.el.code(
                node,
                class_name="bg-gray-100 rounded px-1 py-0.5 font-mono text-sm",
            )

        if isinstance(node, dict):
            inline = bool(node.get("inline", False))
            class_name = node.get("className") or node.get("class_name") or ""
            code_text = _children_to_text(node.get("children"))

            # Extract language from className like `language-javascript`.
            lang = ""
            if isinstance(class_name, str):
                for part in class_name.split():
                    if part.startswith("language-"):
                        lang = part[len("language-") :]
                        break

            raw_lang = (lang or "").strip()
            wrap_long = False
            if raw_lang.endswith("!"):
                wrap_long = True
                raw_lang = raw_lang[:-1]

            show_line_numbers = False
            starting_line_number = None
            if "=" in raw_lang:
                show_line_numbers = True
                raw_lang, start = raw_lang.split("=", 1)
                start = start.strip()
                if start.isdigit():
                    starting_line_number = int(start)
                else:
                    # ```lang=  means start from 1
                    starting_line_number = 1

            lang = (raw_lang or "").strip().lower()

            # Common aliases (HackMD-style convenience).
            aliases = {
                "js": "javascript",
                "ts": "typescript",
                "py": "python",
                "sh": "bash",
                "shell": "bash",
                "zsh": "bash",
                "yml": "yaml",
                "md": "markdown",
                "html": "markup",
                "xml": "markup",
                "c++": "cpp",
                "c#": "csharp",
                "ps1": "powershell",
                "console": "shell-session",
            }
            lang = aliases.get(lang, lang)

            # Safe fallback: Reflex CodeBlock rejects unknown languages.
            # Use `markdown` as a neutral, supported default.
            if not lang:
                lang = "markdown"

            if inline:
                return rx.el.code(
                    code_text,
                    class_name="bg-gray-100 rounded px-1 py-0.5 font-mono text-sm",
                )

            props = {
                "language": lang,
                "wrap_long_lines": wrap_long,
            }
            if show_line_numbers:
                props["show_line_numbers"] = True
                props["starting_line_number"] = starting_line_number or 1

            try:
                return rx.code_block(code_text, **props)
            except TypeError:
                # Unknown language: fall back without crashing.
                props["language"] = "markdown"
                return rx.code_block(code_text, **props)

        # Fallback (should be rare): try rendering as plain inline code.
        return rx.el.code(
            str(node),
            class_name="bg-gray-100 rounded px-1 py-0.5 font-mono text-sm",
        )

    return rx.el.div(
        rx.markdown(
            EditorState.doc_content_rendered,
            component_map={
                "h1": lambda text: rx.el.h1(
                    text, class_name="text-3xl font-bold text-gray-900 mb-4"
                ),
                "h2": lambda text: rx.el.h2(
                    text,
                    class_name="text-2xl font-bold text-gray-800 mt-6 mb-3 pb-1 border-b",
                ),
                "h3": lambda text: rx.el.h3(
                    text, class_name="text-xl font-bold text-gray-800 mt-4 mb-2"
                ),
                "p": lambda text: rx.el.p(
                    text,
                    class_name="mb-4 text-gray-700 leading-relaxed whitespace-pre-wrap",
                ),
                "ul": lambda text: rx.el.ul(
                    text, class_name="list-disc list-inside mb-4 pl-4"
                ),
                "ol": lambda text: rx.el.ol(
                    text, class_name="list-decimal list-inside mb-4 pl-4"
                ),
                "li": lambda text: rx.el.li(
                    text, class_name="mb-1 text-gray-700 whitespace-pre-wrap"
                ),
                "blockquote": lambda text: rx.el.blockquote(
                    text, class_name="border-l-4 border-gray-300 pl-4 italic my-4"
                ),
                "pre": _markdown_pre,
                "code": _markdown_code,
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