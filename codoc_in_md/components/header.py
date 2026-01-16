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


def header() -> rx.Component:
    """The application header, displaying users and document title."""
    return rx.el.header(
        rx.el.div(
            rx.icon("file-text", class_name="h-6 w-6 text-violet-600"),
            rx.el.div(
                rx.el.h1(
                    "Collaborative Doc", class_name="text-xl font-bold text-gray-900"
                ),
                rx.el.div(
                    rx.cond(
                        EditorState.is_connected,
                        rx.el.span("● Live", class_name="text-green-500 mr-1"),
                        rx.el.span(
                            "○ Connecting...", class_name="text-yellow-500 mr-1"
                        ),
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
            rx.el.div(
                rx.foreach(EditorState.users, user_avatar),
                class_name="flex -space-x-2 mr-4",
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
                class_name="bg-violet-600 text-white px-4 py-2 rounded-lg hover:bg-violet-700 transition-colors flex items-center font-medium shadow-sm cursor-pointer active:scale-95",
            ),
            class_name="flex items-center",
        ),
        class_name="h-16 px-4 sm:px-6 lg:px-8 flex items-center justify-between border-b border-gray-200 bg-white shadow-sm",
    )