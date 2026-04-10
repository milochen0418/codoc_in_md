import reflex as rx
from codoc_in_md.state import EditorState


def user_avatar(user: dict) -> rx.Component:
    """Displays a user's avatar with a tooltip."""
    return rx.el.div(
        rx.el.div(
            rx.image(
                src=f"https://api.dicebear.com/9.x/initials/svg?seed={user['name']}",
                class_name="h-8 w-8 rounded-full border-2 border-white",
                alt=user["name"],
            ),
            rx.el.div(
                user["name"],
                class_name="absolute -bottom-8 left-1/2 -translate-x-1/2 px-2 py-1 bg-gray-800 text-white text-xs rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none z-10",
            ),
            class_name="relative",
        ),
        class_name="group",
        title=user["name"],
    )


def sidebar_toggle() -> rx.Component:
    """A button to toggle the sidebar open/closed. Hidden on mobile."""
    return rx.el.button(
        rx.cond(
            EditorState.sidebar_open,
            rx.icon("panel-left-close", class_name="h-4 w-4"),
            rx.icon("panel-left-open", class_name="h-4 w-4"),
        ),
        on_click=EditorState.set_sidebar_open(~EditorState.sidebar_open),
        title=rx.cond(
            EditorState.sidebar_open,
            "Hide sidebar",
            "Show sidebar",
        ),
        class_name="p-2 rounded-md text-gray-500 hover:bg-gray-100 transition-colors hidden md:block",
    )


def view_toggle() -> rx.Component:
    """Toggle buttons for switching between editor, split, and preview views."""
    button_base = "p-2 rounded-md transition-colors"
    active_style = "bg-violet-100 text-violet-700"
    inactive_style = "text-gray-500 hover:bg-gray-100"
    return rx.el.div(
        rx.el.button(
            rx.icon("pencil", class_name="h-4 w-4"),
            class_name=rx.cond(
                EditorState.view_mode == "editor",
                f"{button_base} {active_style}",
                f"{button_base} {inactive_style}",
            ),
            on_click=lambda: EditorState.set_view_mode("editor"),
            title="Editor Only",
        ),
        rx.el.button(
            rx.icon("columns-2", class_name="h-4 w-4"),
            class_name=rx.cond(
                EditorState.view_mode == "split",
                f"{button_base} {active_style}",
                f"{button_base} {inactive_style}",
            ),
            on_click=lambda: EditorState.set_view_mode("split"),
            title="Split View",
        ),
        rx.el.button(
            rx.icon("eye", class_name="h-4 w-4"),
            class_name=rx.cond(
                EditorState.view_mode == "preview",
                f"{button_base} {active_style}",
                f"{button_base} {inactive_style}",
            ),
            on_click=lambda: EditorState.set_view_mode("preview"),
            title="Preview Only",
        ),
        rx.el.button(
            rx.icon("maximize", class_name="h-4 w-4"),
            class_name=f"{button_base} {inactive_style}",
            on_click=rx.call_script(
                "window.codocToggleFullscreen && window.codocToggleFullscreen()"
            ),
            title="Fullscreen Preview (Esc to exit)",
        ),
        class_name="flex items-center gap-1 border-l border-gray-200 pl-3 ml-3 hidden md:flex",
    )


def _dropdown_menu_cls() -> str:
    return (
        "absolute right-0 top-full pt-2 w-44 z-50 hidden group-hover:block"
    )


def _dropdown_inner_cls() -> str:
    return (
        "bg-white border border-gray-200 rounded-lg shadow-lg py-1"
    )


def _dropdown_item_cls() -> str:
    return (
        "w-full text-left flex items-center gap-2 px-4 py-2 text-sm text-gray-700 "
        "hover:bg-gray-50 transition-colors cursor-pointer"
    )


def _header_btn_cls() -> str:
    return (
        "flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-gray-700 "
        "hover:bg-gray-100 rounded-lg transition-colors cursor-pointer"
    )


def document_dropdown() -> rx.Component:
    """Document dropdown: New / Duplicate."""
    return rx.el.div(
        rx.el.button(
            rx.icon("file-text", class_name="h-4 w-4"),
            "Document",
            rx.icon("chevron-down", class_name="h-3 w-3 opacity-50"),
            class_name=_header_btn_cls(),
        ),
        rx.el.div(
            rx.el.div(
                rx.el.button(
                    rx.icon("plus", class_name="h-4 w-4"),
                    "New",
                    on_click=EditorState.create_new_document,
                    class_name=_dropdown_item_cls(),
                ),
                rx.el.button(
                    rx.icon("copy", class_name="h-4 w-4"),
                    "Duplicate",
                    on_click=EditorState.duplicate_document,
                    class_name=_dropdown_item_cls(),
                ),
                class_name=_dropdown_inner_cls(),
            ),
            class_name=_dropdown_menu_cls(),
        ),
        class_name="relative group",
    )


def export_dropdown() -> rx.Component:
    """Export dropdown: Markdown / PDF."""
    return rx.el.div(
        rx.el.button(
            rx.icon("download", class_name="h-4 w-4"),
            "Export",
            rx.icon("chevron-down", class_name="h-3 w-3 opacity-50"),
            class_name=_header_btn_cls(),
        ),
        rx.el.div(
            rx.el.div(
                rx.el.button(
                    rx.icon("file-text", class_name="h-4 w-4"),
                    "Markdown",
                    on_click=EditorState.export_markdown,
                    class_name=_dropdown_item_cls(),
                ),
                rx.el.button(
                    rx.icon("file-output", class_name="h-4 w-4"),
                    "PDF",
                    on_click=rx.call_script(
                        "window.codocExportPdf && window.codocExportPdf()"
                    ),
                    class_name=_dropdown_item_cls(),
                ),
                class_name=_dropdown_inner_cls(),
            ),
            class_name=_dropdown_menu_cls(),
        ),
        class_name="relative group",
    )


def _mobile_menu_item_cls() -> str:
    return (
        "w-full text-left flex items-center gap-3 px-4 py-3 text-sm font-medium "
        "text-gray-700 hover:bg-gray-50 transition-colors"
    )


def mobile_menu_button() -> rx.Component:
    """Hamburger button shown only on mobile."""
    return rx.el.button(
        rx.cond(
            EditorState.mobile_menu_open,
            rx.icon("x", class_name="h-5 w-5"),
            rx.icon("menu", class_name="h-5 w-5"),
        ),
        on_click=EditorState.set_mobile_menu_open(~EditorState.mobile_menu_open),
        class_name="p-2 rounded-md text-gray-500 hover:bg-gray-100 transition-colors md:hidden",
    )


def mobile_menu_panel() -> rx.Component:
    """Full-width dropdown panel for mobile, shown below the header."""
    return rx.cond(
        EditorState.mobile_menu_open,
        rx.el.div(
            # View mode section
            rx.el.div(
                rx.el.p("View", class_name="text-xs font-semibold text-gray-400 uppercase tracking-wider px-4 py-2"),
                rx.el.button(
                    rx.icon("pencil", class_name="h-4 w-4"),
                    "Editor Only",
                    on_click=[EditorState.set_view_mode("editor"), EditorState.set_mobile_menu_open(False)],
                    class_name=_mobile_menu_item_cls(),
                ),
                rx.el.button(
                    rx.icon("columns-2", class_name="h-4 w-4"),
                    "Split View",
                    on_click=[EditorState.set_view_mode("split"), EditorState.set_mobile_menu_open(False)],
                    class_name=_mobile_menu_item_cls(),
                ),
                rx.el.button(
                    rx.icon("eye", class_name="h-4 w-4"),
                    "Preview Only",
                    on_click=[EditorState.set_view_mode("preview"), EditorState.set_mobile_menu_open(False)],
                    class_name=_mobile_menu_item_cls(),
                ),
                class_name="border-b border-gray-100",
            ),
            # Document section
            rx.el.div(
                rx.el.p("Document", class_name="text-xs font-semibold text-gray-400 uppercase tracking-wider px-4 py-2"),
                rx.el.button(
                    rx.icon("plus", class_name="h-4 w-4"),
                    "New Document",
                    on_click=[EditorState.create_new_document, EditorState.set_mobile_menu_open(False)],
                    class_name=_mobile_menu_item_cls(),
                ),
                rx.el.button(
                    rx.icon("copy", class_name="h-4 w-4"),
                    "Duplicate",
                    on_click=[EditorState.duplicate_document, EditorState.set_mobile_menu_open(False)],
                    class_name=_mobile_menu_item_cls(),
                ),
                class_name="border-b border-gray-100",
            ),
            # Export section
            rx.el.div(
                rx.el.p("Export", class_name="text-xs font-semibold text-gray-400 uppercase tracking-wider px-4 py-2"),
                rx.el.button(
                    rx.icon("file-text", class_name="h-4 w-4"),
                    "Markdown",
                    on_click=[EditorState.export_markdown, EditorState.set_mobile_menu_open(False)],
                    class_name=_mobile_menu_item_cls(),
                ),
                rx.el.button(
                    rx.icon("file-output", class_name="h-4 w-4"),
                    "PDF",
                    on_click=[
                        rx.call_script("window.codocExportPdf && window.codocExportPdf()"),
                        EditorState.set_mobile_menu_open(False),
                    ],
                    class_name=_mobile_menu_item_cls(),
                ),
                class_name="border-b border-gray-100",
            ),
            # Other actions
            rx.el.div(
                rx.el.button(
                    rx.icon("share-2", class_name="h-4 w-4"),
                    "Share Link",
                    on_click=[
                        rx.call_script("navigator.clipboard.writeText(window.location.href)"),
                        rx.toast.success("Link copied!", duration=3000, position="bottom-right"),
                        EditorState.set_mobile_menu_open(False),
                    ],
                    class_name=_mobile_menu_item_cls(),
                ),
                rx.el.a(
                    rx.icon("folder-open", class_name="h-4 w-4"),
                    "My Documents",
                    href="/",
                    class_name=_mobile_menu_item_cls(),
                ),
            ),
            class_name="absolute top-full left-0 right-0 bg-white border-b border-gray-200 shadow-lg z-50 md:hidden",
        ),
    )


def header() -> rx.Component:
    """The application header, displaying users and document title."""
    return rx.el.header(
        # --- Top bar ---
        rx.el.div(
            rx.el.div(
                sidebar_toggle(),
                rx.el.div(class_name="w-px h-6 bg-gray-200 hidden md:block"),
                rx.el.a(
                    rx.icon("file-text", class_name="h-6 w-6 text-violet-600"),
                    href="/",
                    title="Back to Documents",
                    class_name="hover:opacity-80 transition-opacity",
                ),
                rx.el.div(
                    rx.el.h1(
                        "Collaborative Doc", class_name="text-xl font-bold text-gray-900 hidden sm:block"
                    ),
                    rx.el.h1(
                        "CoDoc", class_name="text-lg font-bold text-gray-900 sm:hidden"
                    ),
                    rx.el.div(
                        rx.cond(
                            EditorState.is_connected,
                            rx.el.span("● Live", class_name="text-green-500 mr-1"),
                            rx.el.span("○ Connecting...", class_name="text-yellow-500 mr-1"),
                        ),
                        rx.el.span(
                            f"{EditorState.user_count} active", class_name="text-gray-500"
                        ),
                        class_name="text-xs font-medium flex items-center",
                    ),
                ),
                view_toggle(),
                class_name="flex items-center gap-3",
            ),
            rx.el.div(
                # Desktop actions (hidden on mobile)
                rx.el.div(
                    rx.el.div(
                        rx.foreach(EditorState.users, user_avatar),
                        class_name="flex -space-x-2 mr-4",
                    ),
                    document_dropdown(),
                    export_dropdown(),
                    rx.el.button(
                        rx.icon("share-2", class_name="h-4 w-4"),
                        "Share Link",
                        on_click=[
                            rx.call_script("navigator.clipboard.writeText(window.location.href)"),
                            rx.toast.success("Link copied to clipboard!", duration=3000, position="bottom-right"),
                        ],
                        class_name="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium bg-violet-600 text-white rounded-lg hover:bg-violet-700 transition-colors cursor-pointer active:scale-95",
                    ),
                    rx.el.a(
                        rx.icon("folder-open", class_name="h-4 w-4"),
                        "My Documents",
                        href="/",
                        class_name="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-100 transition-colors cursor-pointer",
                    ),
                    class_name="hidden md:flex items-center gap-2",
                ),
                # Mobile hamburger (hidden on desktop)
                mobile_menu_button(),
                class_name="flex items-center gap-2",
            ),
            class_name="h-16 px-4 sm:px-6 lg:px-8 flex items-center justify-between",
        ),
        # --- Mobile dropdown panel ---
        mobile_menu_panel(),
        class_name="relative border-b border-gray-200 bg-white shadow-sm",
    )