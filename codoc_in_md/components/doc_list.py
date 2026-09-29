"""Document management page – lists all saved documents."""

import reflex as rx

from codoc_in_md.components.header import _HAS_INTENT, my_relack_username, open_profile
from codoc_in_md.state import SEARCH_INPUT_ID, DocListState, EditorState

if _HAS_INTENT:
    from reflex_ddns_auth.intent import intent_host

try:
    from reflex_ddns_auth import AuthState
    _HAS_AUTH = True
except ImportError:
    _HAS_AUTH = False


_TH = "px-6 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider"
_SELECT = (
    "h-10 pl-3 pr-8 text-sm text-gray-700 bg-white border border-gray-200 rounded-lg "
    "focus:outline-none focus:ring-2 focus:ring-violet-200 focus:border-violet-400 cursor-pointer"
)


def creator_cell(doc: dict) -> rx.Component:
    """Creator info; clicking it filters the list to that creator."""
    return rx.el.button(
        rx.cond(
            doc["created_by_email"] != "",
            rx.el.div(
                rx.el.span(
                    rx.cond(doc["created_by_name"] != "", doc["created_by_name"], doc["created_by_email"]),
                    class_name="text-gray-700 text-sm font-medium group-hover:text-violet-700",
                ),
                rx.el.span(doc["created_by_email"], class_name="text-gray-400 text-xs block"),
                class_name="text-left",
            ),
            rx.el.div(
                rx.icon("user", class_name="h-3.5 w-3.5 text-gray-400 inline-block mr-1"),
                rx.el.span("Guest", class_name="text-gray-400 text-sm italic group-hover:text-violet-700"),
                class_name="flex items-center gap-1",
            ),
        ),
        on_click=DocListState.filter_by_creator_of(doc["created_by_email"]),
        title="Show all documents by this creator",
        class_name="group -mx-2 px-2 py-1 rounded-md hover:bg-violet-50 transition-colors cursor-pointer",
    )


def doc_row(doc: dict) -> rx.Component:
    """A single row in the document list."""
    return rx.el.tr(
        rx.el.td(
            rx.el.div(
                rx.el.a(
                    doc["title"],
                    href=rx.cond(doc["doc_id"] != "", "/doc/" + doc["doc_id"], "/"),
                    class_name="text-violet-600 hover:text-violet-800 hover:underline font-medium",
                ),
                rx.cond(
                    doc["is_empty"],
                    rx.el.span(
                        "Empty",
                        class_name="text-[10px] font-semibold uppercase tracking-wide text-amber-700 bg-amber-50 border border-amber-200 rounded px-1.5 py-0.5",
                    ),
                ),
                class_name="flex items-center gap-2 flex-wrap",
            ),
            rx.cond(
                doc["snippet"] != "",
                rx.el.p(
                    rx.icon("text-search", class_name="h-3 w-3 inline-block mr-1 -mt-0.5"),
                    doc["snippet"],
                    class_name="mt-1 text-xs text-gray-500 line-clamp-2 max-w-md",
                ),
            ),
            rx.el.p(
                doc["words"].to(str) + " words",
                rx.el.span(" · " + doc["doc_id"], class_name="font-mono md:hidden"),
                class_name="mt-0.5 text-[11px] text-gray-400",
            ),
            class_name="px-6 py-4 align-top",
        ),
        rx.el.td(
            doc["doc_id"],
            class_name="hidden md:table-cell px-6 py-4 text-gray-500 text-sm font-mono align-top",
        ),
        rx.el.td(creator_cell(doc), class_name="px-6 py-3 align-top"),
        rx.el.td(
            doc["formatted_time"],
            class_name="px-6 py-4 text-gray-500 text-sm whitespace-nowrap align-top",
        ),
        rx.el.td(
            rx.el.button(
                rx.icon("trash-2", class_name="h-4 w-4"),
                on_click=DocListState.delete_document(doc["doc_id"]),
                class_name="p-2 text-red-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors cursor-pointer",
                title="Delete document",
            ),
            class_name="px-6 py-3 text-center align-top",
        ),
        class_name="border-b border-gray-100 hover:bg-gray-50/60 transition-colors",
    )


def creator_chip(opt: dict) -> rx.Component:
    active = DocListState.creator_filter == opt["key"]
    return rx.el.button(
        rx.cond(
            opt["key"] == "guest",
            rx.icon("user", class_name="h-3.5 w-3.5"),
            rx.cond(opt["key"] == "mine", rx.icon("star", class_name="h-3.5 w-3.5")),
        ),
        rx.el.span(opt["label"]),
        rx.el.span(
            opt["count"],
            class_name=rx.cond(
                active,
                "text-[11px] px-1.5 rounded-full bg-white/25",
                "text-[11px] px-1.5 rounded-full bg-gray-100 text-gray-500",
            ),
        ),
        on_click=DocListState.set_creator_filter(opt["key"]),
        title=opt["sublabel"],
        class_name=rx.cond(
            active,
            "flex items-center gap-1.5 h-8 px-3 text-sm font-medium rounded-full bg-violet-600 text-white border border-violet-600 cursor-pointer",
            "flex items-center gap-1.5 h-8 px-3 text-sm rounded-full bg-white text-gray-700 border border-gray-200 hover:border-violet-300 hover:text-violet-700 cursor-pointer transition-colors",
        ),
    )


def filter_bar() -> rx.Component:
    return rx.el.div(
        # Search + selects
        rx.el.div(
            rx.el.div(
                rx.icon("search", class_name="h-4 w-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none"),
                # Uncontrolled on purpose: binding `value` to backend state makes every
                # keystroke wait for a round-trip (and debounced events drop characters).
                rx.el.input(
                    id=SEARCH_INPUT_ID,
                    default_value=DocListState.search,
                    on_change=DocListState.set_search.debounce(250),
                    placeholder="Search title, content, doc ID or creator…",
                    class_name=(
                        "w-full h-10 pl-9 pr-9 text-sm bg-white border border-gray-200 rounded-lg "
                        "focus:outline-none focus:ring-2 focus:ring-violet-200 focus:border-violet-400"
                    ),
                ),
                rx.cond(
                    DocListState.search != "",
                    rx.el.button(
                        rx.icon("x", class_name="h-4 w-4"),
                        on_click=DocListState.clear_search,
                        title="Clear search",
                        class_name="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-gray-400 hover:text-gray-600 cursor-pointer",
                    ),
                ),
                class_name="relative flex-1 min-w-[200px]",
            ),
            rx.el.select(
                rx.el.option("Updated: any time", value="any"),
                rx.el.option("Updated today", value="today"),
                rx.el.option("Last 7 days", value="7d"),
                rx.el.option("Last 30 days", value="30d"),
                rx.el.option("Older than 30 days", value="older"),
                value=DocListState.time_filter,
                on_change=DocListState.set_time_filter,
                class_name=_SELECT,
                aria_label="Filter by last update",
            ),
            rx.el.select(
                rx.el.option("Newest first", value="updated_desc"),
                rx.el.option("Oldest first", value="updated_asc"),
                rx.el.option("Title A → Z", value="title_asc"),
                rx.el.option("Title Z → A", value="title_desc"),
                value=DocListState.sort_by,
                on_change=DocListState.set_sort_by,
                class_name=_SELECT,
                aria_label="Sort documents",
            ),
            class_name="flex flex-wrap items-center gap-2",
        ),
        # Creator facets + empty toggle
        rx.el.div(
            rx.el.span("Created by", class_name="text-xs font-semibold uppercase tracking-wider text-gray-400 mr-1"),
            rx.foreach(DocListState.creator_options, creator_chip),
            rx.cond(
                DocListState.empty_count > 0,
                rx.fragment(
                    rx.el.span(class_name="w-px h-5 bg-gray-200 mx-1"),
                    rx.el.button(
                        rx.icon("file-x", class_name="h-3.5 w-3.5"),
                        rx.el.span("Empty only"),
                        rx.el.span(DocListState.empty_count, class_name="text-[11px] px-1.5 rounded-full bg-amber-100 text-amber-700"),
                        on_click=DocListState.toggle_only_empty,
                        title="Documents still holding the default placeholder",
                        class_name=rx.cond(
                            DocListState.only_empty,
                            "flex items-center gap-1.5 h-8 px-3 text-sm font-medium rounded-full bg-amber-500 text-white border border-amber-500 cursor-pointer",
                            "flex items-center gap-1.5 h-8 px-3 text-sm rounded-full bg-white text-gray-700 border border-gray-200 hover:border-amber-300 hover:text-amber-700 cursor-pointer transition-colors",
                        ),
                    ),
                ),
            ),
            class_name="flex flex-wrap items-center gap-2 mt-3",
        ),
        class_name="bg-white border border-gray-200 rounded-lg shadow-sm p-3 sm:p-4 mb-4",
    )


def delete_filtered_button() -> rx.Component:
    """Bulk delete of the current filtered view, behind a confirmation."""
    return rx.alert_dialog.root(
        rx.alert_dialog.trigger(
            rx.el.button(
                rx.icon("trash", class_name="mr-2 h-4 w-4"),
                "Delete " + DocListState.documents.length().to(str) + " shown",
                class_name="text-sm text-red-500 hover:text-red-700 hover:bg-red-50 px-3 py-1.5 rounded transition-colors flex items-center cursor-pointer border border-red-200",
            ),
        ),
        rx.alert_dialog.content(
            rx.alert_dialog.title("Delete filtered documents?"),
            rx.alert_dialog.description(
                "This permanently deletes the "
                + DocListState.documents.length().to(str)
                + " document(s) matching the current filters. Other documents are kept.",
            ),
            rx.el.div(
                rx.alert_dialog.cancel(
                    rx.el.button("Cancel", class_name="px-4 py-2 text-sm rounded-lg border border-gray-200 hover:bg-gray-50 cursor-pointer"),
                ),
                rx.alert_dialog.action(
                    rx.el.button(
                        "Delete",
                        on_click=DocListState.delete_filtered_documents,
                        class_name="px-4 py-2 text-sm rounded-lg bg-red-600 text-white hover:bg-red-700 cursor-pointer",
                    ),
                ),
                class_name="flex justify-end gap-2 mt-4",
            ),
        ),
    )


def summary_bar() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.p(
                rx.cond(
                    DocListState.total_count == 0,
                    "No documents yet",
                    rx.cond(
                        DocListState.has_active_filters,
                        "Showing "
                        + DocListState.documents.length().to(str)
                        + " of "
                        + DocListState.total_count.to(str)
                        + " document(s)",
                        DocListState.total_count.to(str) + " document(s)",
                    ),
                ),
                class_name="text-sm text-gray-500",
            ),
            rx.cond(
                DocListState.has_active_filters,
                rx.el.button(
                    rx.icon("rotate-ccw", class_name="h-3.5 w-3.5 mr-1"),
                    "Reset filters",
                    on_click=DocListState.reset_filters,
                    class_name="flex items-center text-sm text-violet-600 hover:text-violet-800 cursor-pointer",
                ),
            ),
            class_name="flex items-center gap-3",
        ),
        rx.cond(
            DocListState.has_active_filters,
            rx.cond(DocListState.documents.length() > 0, delete_filtered_button()),
            rx.cond(
                DocListState.total_count > 0,
                rx.el.button(
                    rx.icon("trash", class_name="mr-2 h-4 w-4"),
                    "Clear All",
                    on_click=DocListState.clear_all_documents,
                    class_name="text-sm text-red-500 hover:text-red-700 hover:bg-red-50 px-3 py-1.5 rounded transition-colors flex items-center cursor-pointer border border-red-200",
                ),
            ),
        ),
        class_name="flex items-center justify-between gap-3 flex-wrap mb-3",
    )


def doc_table() -> rx.Component:
    return rx.el.div(
        rx.el.table(
            rx.el.thead(
                rx.el.tr(
                    rx.el.th("Title", class_name=_TH),
                    rx.el.th("Doc ID", class_name="hidden md:table-cell " + _TH),
                    rx.el.th("Created By", class_name=_TH),
                    rx.el.th("Updated", class_name=_TH),
                    rx.el.th("", class_name="px-6 py-3 w-16"),
                    class_name="border-b border-gray-200",
                ),
                class_name="bg-gray-50",
            ),
            rx.el.tbody(rx.foreach(DocListState.documents, doc_row)),
            class_name="min-w-full",
        ),
        class_name="bg-white rounded-lg border border-gray-200 overflow-x-auto shadow-sm",
    )


def no_match_state() -> rx.Component:
    return rx.el.div(
        rx.icon("search-x", class_name="h-12 w-12 text-gray-300 mb-3"),
        rx.el.p("No documents match these filters", class_name="text-base font-medium text-gray-500 mb-4"),
        rx.el.button(
            rx.icon("rotate-ccw", class_name="mr-2 h-4 w-4"),
            "Reset filters",
            on_click=DocListState.reset_filters,
            class_name="px-4 py-2 text-sm rounded-lg border border-violet-200 text-violet-700 hover:bg-violet-50 flex items-center cursor-pointer",
        ),
        class_name="flex flex-col items-center justify-center py-16 bg-white rounded-lg border border-dashed border-gray-200",
    )


def empty_state() -> rx.Component:
    return rx.el.div(
        rx.icon("file-plus", class_name="h-16 w-16 text-gray-300 mb-4"),
        rx.el.p("No documents yet", class_name="text-lg font-medium text-gray-500 mb-2"),
        rx.el.p("Create a new document to get started.", class_name="text-sm text-gray-400 mb-6"),
        rx.el.button(
            rx.icon("plus", class_name="mr-2 h-4 w-4"),
            "Create Document",
            on_click=EditorState.create_new_document,
            class_name="bg-violet-600 text-white px-6 py-2.5 rounded-lg hover:bg-violet-700 transition-colors flex items-center font-medium shadow-sm cursor-pointer",
        ),
        class_name="flex flex-col items-center justify-center py-20",
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
                        *(
                            [rx.cond(
                                AuthState.is_logged_in,
                                rx.el.div(
                                    rx.el.div(
                                        rx.cond(
                                            AuthState.user_avatar != "",
                                            rx.image(
                                                src=AuthState.user_avatar,
                                                class_name="h-8 w-8 rounded-full border-2 border-violet-200",
                                            ),
                                            rx.image(
                                                src=rx.cond(
                                                    AuthState.user_name != "",
                                                    "https://api.dicebear.com/9.x/initials/svg?seed=" + AuthState.user_name,
                                                    "https://api.dicebear.com/9.x/initials/svg?seed=U",
                                                ),
                                                class_name="h-8 w-8 rounded-full border-2 border-violet-200",
                                            ),
                                        ),
                                        on_click=open_profile(my_relack_username()),
                                        title="View profile",
                                        class_name="cursor-pointer" if _HAS_INTENT else "",
                                    ),
                                    rx.el.span(
                                        AuthState.user_name,
                                        class_name="text-sm font-medium text-gray-700",
                                    ),
                                    rx.el.a(
                                        "Logout",
                                        href=AuthState.logout_url,
                                        class_name=(
                                            "ml-1 px-2 py-1 text-xs font-medium text-gray-500 "
                                            "hover:text-red-600 hover:bg-red-50 rounded transition-colors"
                                        ),
                                    ),
                                    class_name="flex items-center gap-2 mr-3",
                                ),
                                rx.el.div(
                                    rx.icon("user", class_name="h-5 w-5 text-gray-400"),
                                    rx.el.span("Guest", class_name="text-sm font-medium text-gray-500"),
                                    rx.el.a(
                                        "Login",
                                        href=AuthState.login_url,
                                        class_name=(
                                            "ml-2 px-3 py-1 text-xs font-medium text-white bg-violet-600 "
                                            "rounded-md hover:bg-violet-700 transition-colors"
                                        ),
                                    ),
                                    class_name="flex items-center gap-2 mr-3",
                                ),
                            )] if _HAS_AUTH else []
                        ),
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
                    rx.cond(DocListState.total_count > 0, filter_bar()),
                    summary_bar(),
                    rx.cond(
                        DocListState.documents.length() > 0,
                        doc_table(),
                        rx.cond(DocListState.total_count > 0, no_match_state(), empty_state()),
                    ),
                    class_name="max-w-5xl mx-auto w-full",
                ),
                class_name="flex-1 px-4 sm:px-6 lg:px-8 py-8 bg-gray-50 overflow-y-auto",
            ),
            class_name="flex flex-col h-screen w-full bg-white",
        ),
        *([intent_host()] if _HAS_INTENT else []),
        class_name="font-['Raleway']",
    )
