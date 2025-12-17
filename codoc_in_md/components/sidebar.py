import reflex as rx
from codoc_in_md.state import EditorState


def sidebar() -> rx.Component:
    """A sidebar component for document settings and info."""
    return rx.el.aside(
        rx.el.div(
            rx.el.h2("Document", class_name="text-lg font-semibold text-gray-900"),
            rx.el.div(
                rx.el.span("ID: ", class_name="text-gray-500"),
                rx.el.span(
                    EditorState.doc_id, class_name="font-mono text-gray-700 select-all"
                ),
                class_name="text-xs mt-1",
            ),
            class_name="p-4 border-b border-gray-200",
        ),
        rx.el.div(
            rx.el.h3(
                "Actions",
                class_name="text-sm font-semibold text-gray-500 uppercase tracking-wider px-4 mb-2",
            ),
            rx.el.button(
                rx.icon("circle_plus", class_name="mr-2 h-4 w-4"),
                "New Document",
                on_click=EditorState.create_new_document,
                class_name="w-full text-left flex items-center px-4 py-2 text-sm font-medium text-violet-700 bg-violet-50 hover:bg-violet-100 rounded-md mb-2",
            ),
            rx.el.button(
                rx.icon("download", class_name="mr-2 h-4 w-4"),
                "Export as Markdown",
                class_name="w-full text-left flex items-center px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded-md",
            ),
            rx.el.button(
                rx.icon("share-2", class_name="mr-2 h-4 w-4"),
                "Share Link",
                on_click=[
                    rx.call_script(
                        "navigator.clipboard.writeText(window.location.href)"
                    ),
                    rx.toast.success(
                        "Link copied to clipboard!",
                        duration=3000,
                        position="bottom-right",
                    ),
                ],
                class_name="w-full text-left flex items-center px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded-md",
            ),
            class_name="p-2",
        ),
        rx.el.div(
            rx.el.h3(
                "Info",
                class_name="text-sm font-semibold text-gray-500 uppercase tracking-wider px-4 mb-2",
            ),
            rx.el.div(
                rx.el.p("Word Count", class_name="text-sm font-medium text-gray-700"),
                rx.el.p(
                    EditorState.doc_content.split().length(),
                    class_name="text-sm font-semibold text-gray-900",
                ),
                class_name="flex justify-between items-center px-4 py-2",
            ),
            rx.el.div(
                rx.el.p(
                    "Character Count", class_name="text-sm font-medium text-gray-700"
                ),
                rx.el.p(
                    EditorState.doc_content.length(),
                    class_name="text-sm font-semibold text-gray-900",
                ),
                class_name="flex justify-between items-center px-4 py-2",
            ),
            rx.el.div(
                rx.el.p("My Session", class_name="text-sm font-medium text-gray-700"),
                rx.el.div(
                    rx.el.div(
                        class_name="w-2 h-2 rounded-full mr-2",
                        style={"background-color": EditorState.my_user_color},
                    ),
                    rx.el.span(
                        EditorState.my_user_name,
                        class_name="text-xs text-gray-500 truncate max-w-[100px]",
                    ),
                    class_name="flex items-center",
                ),
                class_name="flex justify-between items-center px-4 py-2 border-t border-gray-100",
            ),
            class_name="p-2 border-t border-gray-200 mt-auto",
        ),
        class_name="w-64 bg-gray-50 border-r border-gray-200 flex flex-col h-full",
    )