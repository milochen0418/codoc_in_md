import reflex as rx
from reflex_monaco import monaco
from codoc_in_md.state import EditorState
from codoc_in_md.components.header import header
from codoc_in_md.components.sidebar import sidebar


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
                "code": lambda text: rx.el.code(
                    text, class_name="bg-gray-100 rounded px-1 py-0.5 font-mono text-sm"
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


def embed_sequence() -> rx.Component:
    """Client-side sequence diagram renderer (for iframe embedding)."""

    return rx.el.div(
        rx.el.div(id="diagram", class_name="w-full"),
        rx.el.script(src="https://bramp.github.io/js-sequence-diagrams/js/webfont.js"),
        rx.el.script(src="https://bramp.github.io/js-sequence-diagrams/js/snap.svg-min.js"),
        rx.el.script(src="https://bramp.github.io/js-sequence-diagrams/js/underscore-min.js"),
        rx.el.script(src="https://bramp.github.io/js-sequence-diagrams/js/sequence-diagram-min.js"),
        rx.el.script(
            """
            (function(){
              try {
                var params = new URLSearchParams(window.location.search);
                var code = params.get('code') || '';
                code = decodeURIComponent(code);
                if (!code) return;
                var d = Diagram.parse(code);
                d.drawSVG('diagram', { theme: 'simple' });
              } catch (e) {
                var pre = document.createElement('pre');
                pre.textContent = (new URLSearchParams(window.location.search)).get('code') || '';
                document.body.appendChild(pre);
              }
            })();
            """,
        ),
        style={"padding": "12px", "fontFamily": "sans-serif"},
    )


def embed_gist() -> rx.Component:
    """Client-side gist renderer (for iframe embedding)."""

    return rx.el.div(
        rx.el.script(
            """
            (function(){
              var params = new URLSearchParams(window.location.search);
              var url = params.get('url') || '';
              try { url = decodeURIComponent(url); } catch (e) {}
              if (!url) return;
              var s = document.createElement('script');
              s.src = url;
              document.body.appendChild(s);
            })();
            """,
        ),
        style={"margin": "0", "padding": "0"},
    )

app.add_page(index, route="/doc/[document_id]", on_load=EditorState.on_load)
app.add_page(index, route="/", on_load=EditorState.on_load)
app.add_page(embed_sequence, route="/__embed/sequence")
app.add_page(embed_gist, route="/__embed/gist")