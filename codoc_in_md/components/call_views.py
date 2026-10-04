"""Call controls: call everyone on the document, incoming calls, call heartbeat."""

import reflex as rx

from codoc_in_md.call import CALLS_ENABLED, CallState


def call_button() -> rx.Component:
    """Call everyone on the document, or join its call while one is in progress."""
    if not CALLS_ENABLED:
        return rx.fragment()
    return rx.cond(
        CallState.call_count > 0,
        rx.el.button(
            rx.icon("phone-call", class_name="h-4 w-4"),
            "Join call · ",
            CallState.call_count,
            on_click=CallState.join_call,
            class_name="flex items-center gap-1.5 px-3 py-1.5 text-sm font-semibold text-white bg-green-600 rounded-lg hover:bg-green-700 transition-colors whitespace-nowrap shrink-0",
        ),
        rx.el.button(
            rx.icon("phone", class_name="h-4 w-4"),
            "Call everyone",
            on_click=CallState.join_call,
            title="Call everyone on this document",
            class_name="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-gray-700 border border-gray-300 rounded-lg hover:bg-green-50 hover:text-green-700 hover:border-green-300 transition-colors whitespace-nowrap shrink-0",
        ),
    )


def mobile_call_item(item_class: str, close_menu) -> rx.Component:
    """The call button as an item of the mobile menu."""
    if not CALLS_ENABLED:
        return rx.fragment()
    return rx.el.button(
        rx.icon("phone", class_name="h-4 w-4"),
        rx.cond(CallState.call_count > 0, "Join call", "Call everyone"),
        on_click=[CallState.join_call, close_menu],
        class_name=item_class,
    )


def incoming_call() -> rx.Component:
    """Someone called everyone on the document: accept or decline."""
    if not CALLS_ENABLED:
        return rx.fragment()
    # Above the intent dialog (z-index 1000), so a call can be answered from inside another.
    return rx.cond(
        CallState.ringing_from != "",
        rx.el.div(
            rx.el.div(
                rx.icon("phone-incoming", class_name="h-5 w-5 text-white"),
                class_name="size-10 rounded-full bg-green-500 flex items-center justify-center shrink-0 animate-pulse",
            ),
            rx.el.div(
                rx.el.span(
                    "Incoming call",
                    class_name="text-xs font-semibold uppercase tracking-wide text-green-600",
                ),
                rx.el.span(CallState.ringing_from, class_name="text-sm font-bold text-gray-900 truncate"),
                rx.el.span("is calling everyone here", class_name="text-xs text-gray-500"),
                class_name="flex flex-col min-w-0 flex-1",
            ),
            rx.el.button(
                rx.icon("phone-off", class_name="h-4 w-4"),
                on_click=CallState.decline_call,
                title="Decline",
                aria_label="Decline",
                class_name="p-2.5 rounded-full bg-red-100 text-red-600 hover:bg-red-200 transition-colors shrink-0",
            ),
            rx.el.button(
                rx.icon("phone", class_name="h-4 w-4"),
                on_click=CallState.join_call,
                title="Accept",
                aria_label="Accept",
                class_name="p-2.5 rounded-full bg-green-600 text-white hover:bg-green-700 transition-colors shrink-0",
            ),
            role="alertdialog",
            aria_label="Incoming call",
            class_name="fixed bottom-6 right-6 z-[1001] w-80 flex items-center gap-3 p-3 bg-white rounded-2xl border border-gray-100 shadow-2xl",
        ),
    )


_CALL_HEARTBEAT_JS = """
if (window.__codocCallHb) clearInterval(window.__codocCallHb);
window.__codocCallHb = setInterval(function () {
    var el = document.getElementById('call-heartbeat-trigger');
    if (!el) { clearInterval(window.__codocCallHb); window.__codocCallHb = null; return; }
    el.click();
}, 3000);
"""


@rx.memo
def call_keepalive() -> rx.Component:
    """While in a call, keep its heartbeat going on every page.

    The call runs in the app-wide intent dialogs, so it outlives the document
    page; the heartbeat stops with the tab, which then drops out of the call.
    """
    return rx.cond(
        CallState.current_doc != "",
        rx.el.button(
            id="call-heartbeat-trigger",
            on_click=CallState.heartbeat,
            on_mount=rx.call_script(_CALL_HEARTBEAT_JS),
            tab_index=-1,
            aria_hidden="true",
            class_name="sr-only",
        ),
    )
