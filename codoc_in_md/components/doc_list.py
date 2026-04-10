"""Document management page – lists all saved documents."""

import reflex as rx

from codoc_in_md.state import DocListState, EditorState


def doc_row(doc: dict) -> rx.Component:
    """A single row in the document list."""
    return rx.el.tr(
        rx.el.td(
            rx.el.a(
                doc["title"],
                href=rx.cond(doc["doc_id"] != "", "/doc/" + doc["doc_id"], "/"),
                class_name="text-violet-600 hover:text-violet-800 hover:underline font-medium",
            ),
            class_name="px-6 py-4",
        ),
        rx.el.td(
            doc["doc_id"],
            class_name="px-6 py-4 text-gray-500 text-sm font-mono",
        ),
        rx.el.td(
            doc["formatted_time"],
            class_name="px-6 py-4 text-gray-500 text-sm",
        ),
        rx.el.td(
            rx.el.button(
                rx.icon("trash-2", class_name="h-4 w-4"),
                on_click=DocListState.delete_document(doc["doc_id"]),
                class_name="p-2 text-red-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors cursor-pointer",
                title="Delete document",
            ),
            class_name="px-6 py-4 text-center",
        ),
        class_name="border-b border-gray-100 hover:bg-gray-50/60 transition-colors",
    )


def doc_list_page() -> rx.Component:
    """The full document management page."""
    return rx.el.main(
        rx.el.div(
            # Header bar
            rx.el.header(
                rx.el.div(
                    rx.el.div(
                        rx.icon("file-text", class_name="h-6 w-6 text-violet-600"),
                        rx.el.h1(
                            "Document Manager",
                            class_name="text-xl font-bold text-gray-900",
                        ),
                        class_name="flex items-center gap-3",
                    ),
                    rx.el.div(
                        rx.el.button(
                            rx.icon("plus", class_name="mr-2 h-4 w-4"),
                            "New Document",
                            on_click=EditorState.create_new_document,
                            class_name="bg-violet-600 text-white px-4 py-2 rounded-lg hover:bg-violet-700 transition-colors flex items-center font-medium shadow-sm cursor-pointer active:scale-95",
                        ),
                        class_name="flex items-center gap-3",
                    ),
                    class_name="flex items-center justify-between w-full",
                ),
                class_name="h-16 px-4 sm:px-6 lg:px-8 flex items-center border-b border-gray-200 bg-white shadow-sm",
            ),
            # Content
            rx.el.div(
                rx.el.div(
                    # Stats + actions bar
                    rx.el.div(
                        rx.el.p(
                            rx.cond(
                                DocListState.documents.length() > 0,
                                DocListState.documents.length().to(str) + " document(s)",
                                "No documents yet",
                            ),
                            class_name="text-sm text-gray-500",
                        ),
                        rx.cond(
                            DocListState.documents.length() > 0,
                            rx.el.button(
                                rx.icon("trash", class_name="mr-2 h-4 w-4"),
                                "Clear All",
                                on_click=DocListState.clear_all_documents,
                                class_name="text-sm text-red-500 hover:text-red-700 hover:bg-red-50 px-3 py-1.5 rounded transition-colors flex items-center cursor-pointer border border-red-200",
                            ),
                        ),
                        class_name="flex items-center justify-between mb-4",
                    ),
                    # Table
                    rx.cond(
                        DocListState.documents.length() > 0,
                        rx.el.div(
                            rx.el.table(
                                rx.el.thead(
                                    rx.el.tr(
                                        rx.el.th(
                                            "Title",
                                            class_name="px-6 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider",
                                        ),
                                        rx.el.th(
                                            "Doc ID",
                                            class_name="px-6 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider",
                                        ),
                                        rx.el.th(
                                            "Updated",
                                            class_name="px-6 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider",
                                        ),
                                        rx.el.th(
                                            "",
                                            class_name="px-6 py-3 w-16",
                                        ),
                                        class_name="border-b border-gray-200",
                                    ),
                                    class_name="bg-gray-50",
                                ),
                                rx.el.tbody(
                                    rx.foreach(DocListState.documents, doc_row),
                                ),
                                class_name="min-w-full",
                            ),
                            class_name="bg-white rounded-lg border border-gray-200 overflow-hidden shadow-sm",
                        ),
                        # Empty state
                        rx.el.div(
                            rx.icon("file-plus", class_name="h-16 w-16 text-gray-300 mb-4"),
                            rx.el.p(
                                "No documents yet",
                                class_name="text-lg font-medium text-gray-500 mb-2",
                            ),
                            rx.el.p(
                                "Create a new document to get started.",
                                class_name="text-sm text-gray-400 mb-6",
                            ),
                            rx.el.button(
                                rx.icon("plus", class_name="mr-2 h-4 w-4"),
                                "Create Document",
                                on_click=EditorState.create_new_document,
                                class_name="bg-violet-600 text-white px-6 py-2.5 rounded-lg hover:bg-violet-700 transition-colors flex items-center font-medium shadow-sm cursor-pointer",
                            ),
                            class_name="flex flex-col items-center justify-center py-20",
                        ),
                    ),
                    class_name="max-w-5xl mx-auto w-full",
                ),
                class_name="flex-1 px-4 sm:px-6 lg:px-8 py-8 bg-gray-50 overflow-y-auto",
            ),
            class_name="flex flex-col h-screen w-full bg-white",
        ),
        class_name="font-['Raleway']",
    )
