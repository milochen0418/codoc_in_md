"""AI controls (through the AI Hub of re_ddns, see ``ai.py``): the header's AI menu, the writer that
works on the selection, and the note that takes back what the assistant changed. Without the AI
they render nothing."""

from __future__ import annotations

from typing import Any

import reflex as rx

from .. import ai
from ..ai_state import AiState
from ..state import EditorState

try:
    from reflex_ddns_auth.companion import summon
    from reflex_ddns_auth.intent import Intent
except ImportError:  # no platform: no assistant
    Intent = summon = None

AVAILABLE = ai.ENABLED and Intent is not None
VIOLET = "#7C3AED"


def open_assistant() -> Any:
    """Opens the AI Hub's assistant on this document (the ``ai.assist`` intent), in a dialog that
    stays open beside it."""
    return Intent.start(None, "ai.assist", keep_alive=True, single=True, label="AI assistant", in_app=ai.APP, room=EditorState.doc_id)


def open_talk() -> Any:
    """Calls up the AI Hub's talking AI on this document (the ``ai.talk`` intent)."""
    return summon(room=EditorState.doc_id)


def open_writer() -> Any:
    return rx.call_script("window.codocAi && window.codocAi.open()")


def _key(text: str) -> rx.Component:
    return rx.el.span(text, class_name="ml-auto text-xs text-gray-400")


def ai_dropdown(item_cls: str, button_cls: str, menu_cls: str, inner_cls: str) -> rx.Component:
    """The header's AI menu: the assistant, the writer (in the editor), the talking AI."""
    if not AVAILABLE:
        return rx.fragment()
    return rx.el.div(
        rx.el.button(
            rx.icon("sparkles", class_name="h-4 w-4 text-violet-600"),
            "AI",
            rx.icon("chevron-down", class_name="h-3 w-3 opacity-50"),
            class_name=button_cls,
        ),
        rx.el.div(
            rx.el.div(
                rx.el.button(
                    rx.icon("message-circle", class_name="h-4 w-4"),
                    "Assistant",
                    _key("⌥A"),
                    on_click=open_assistant(),
                    title="Ask the AI about this document, or have it write in it (Alt+A)",
                    id="ai-assist",
                    custom_attrs={"data-room": EditorState.doc_id},
                    class_name=item_cls,
                ),
                rx.cond(
                    EditorState.view_mode != "preview",
                    rx.el.button(
                        rx.icon("pen-line", class_name="h-4 w-4"),
                        "Rewrite",
                        _key("⌘I"),
                        on_click=open_writer(),
                        title="Have the AI rewrite what is selected, or write at the caret (Cmd/Ctrl+I)",
                        id="ai-rewrite",
                        class_name=item_cls,
                    ),
                ),
                rx.el.button(
                    rx.icon("mic", class_name="h-4 w-4"),
                    "Talk",
                    on_click=open_talk(),
                    title="Talk with the AI about this document",
                    id="ai-talk",
                    class_name=item_cls,
                ),
                class_name=inner_cls,
            ),
            class_name=menu_cls,
        ),
        class_name="relative group",
    )


def mobile_ai_items(item_cls: str, close: Any) -> list[rx.Component]:
    """The AI's entries in the phone menu (the writer needs the desktop editor's selection)."""
    if not AVAILABLE:
        return []
    return [
        rx.el.button(
            rx.icon("sparkles", class_name="h-4 w-4 text-violet-600"),
            "AI assistant",
            on_click=[open_assistant(), close],
            class_name=item_cls,
        ),
        rx.el.button(
            rx.icon("mic", class_name="h-4 w-4"),
            "Talk with the AI",
            on_click=[open_talk(), close],
            class_name=item_cls,
        ),
    ]


def _quick(name: str, label: str) -> rx.Component:
    return rx.el.button(
        label,
        type="button",
        on_click=AiState.quick(name),
        custom_attrs={"data-quick": name},
        class_name="px-2 py-1 text-xs font-medium text-violet-700 bg-violet-50 border border-violet-200 rounded-md hover:bg-violet-100 transition-colors whitespace-nowrap",
    )


def _quick_row(actions: dict) -> rx.Component:
    return rx.el.div(*[_quick(name, label) for name, (label, _) in actions.items()], class_name="flex flex-wrap gap-1.5")


def _run(run: rx.Var) -> rx.Component:
    return rx.match(
        run["op"].to(str),
        ("new", rx.el.span(run["text"].to(str), class_name="bg-emerald-100 text-emerald-900")),
        ("gone", rx.el.span(run["text"].to(str), class_name="bg-red-50 text-red-400 line-through")),
        rx.el.span(run["text"].to(str)),
    )


def _result() -> rx.Component:
    """The answer as it is written, then as a change to the selection."""
    box = "max-h-[40vh] overflow-y-auto text-sm text-gray-800 whitespace-pre-wrap break-words bg-gray-50 border border-gray-200 rounded-md p-2"
    return rx.match(
        AiState.status,
        (
            "writing",
            rx.cond(
                AiState.answer != "",
                rx.el.div(AiState.answer, id="ai-answer", class_name=box),
                rx.el.div(
                    rx.icon("loader-circle", class_name="h-4 w-4 animate-spin text-violet-600 shrink-0"),
                    rx.el.span("Waiting for the AI. A model that thinks first can take a minute."),
                    id="ai-waiting",
                    class_name="flex items-center gap-2 text-sm text-gray-500",
                ),
            ),
        ),
        ("done", rx.el.div(rx.foreach(AiState.runs, _run), id="ai-answer", class_name=box)),
        ("error", rx.el.div(AiState.error, id="ai-error", class_name="text-sm text-red-700 bg-red-50 border border-red-200 rounded-md p-2 whitespace-pre-wrap")),
        rx.fragment(),
    )


def _actions() -> rx.Component:
    """What to do with an answer. Stop while it is being written."""
    primary = "flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-white bg-violet-600 rounded-md hover:bg-violet-700 transition-colors whitespace-nowrap"
    plain = "flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-gray-700 border border-gray-300 rounded-md hover:bg-gray-100 transition-colors whitespace-nowrap"
    return rx.el.div(
        rx.cond(
            AiState.status == "writing",
            rx.el.button("Stop", rx.el.span("Esc", class_name="text-xs opacity-60"), type="button", on_click=AiState.stop, id="ai-stop", class_name=plain),
        ),
        rx.cond(
            AiState.status == "done",
            rx.fragment(
                rx.el.button(
                    rx.cond(AiState.selected != "", "Replace", "Insert"),
                    rx.el.span("⌘↵", class_name="text-xs opacity-70"),
                    type="button",
                    on_click=AiState.accept(False),
                    id="ai-accept",
                    class_name=primary,
                ),
                rx.cond(
                    AiState.selected != "",
                    rx.el.button("Insert below", type="button", on_click=AiState.accept(True), id="ai-below", class_name=plain),
                ),
                rx.el.button("Discard", rx.el.span("Esc", class_name="text-xs opacity-60"), type="button", on_click=AiState.close_writer, id="ai-discard", class_name=plain),
            ),
        ),
        rx.el.span(AiState.model, id="ai-model", title="Which model answers is chosen on the AI Hub's page", class_name="ml-auto text-xs text-gray-400 truncate"),
        class_name="flex items-center gap-2 min-h-[2rem]",
    )


def ai_writer() -> rx.Component:
    """The writer, next to the selection (``assets/ai_writer.js`` places it). The words are read
    from the form when it is sent: a value echoed back while typing breaks IME composition."""
    if not ai.ENABLED:
        return rx.fragment()
    return rx.fragment(
        rx.el.button(
            on_click=rx.call_script("window.codocAi && window.codocAi.take()", callback=AiState.open_writer),
            # Leaving the document leaves the place the writer works on behind.
            on_unmount=AiState.close_writer,
            type="button",
            id="ai-writer-open",
            class_name="hidden",
        ),
        rx.cond(
            AiState.writer_open,
            rx.el.div(
                rx.el.div(
                    rx.icon("sparkles", class_name="h-4 w-4 text-violet-600 shrink-0"),
                    rx.el.span(AiState.where, id="ai-where", class_name="text-xs font-medium text-gray-500 truncate"),
                    rx.el.button(
                        rx.icon("x", class_name="h-4 w-4"),
                        type="button",
                        on_click=AiState.close_writer,
                        title="Close (Esc)",
                        id="ai-close",
                        class_name="ml-auto p-1 rounded text-gray-400 hover:bg-gray-100",
                    ),
                    class_name="flex items-center gap-2",
                ),
                _result(),
                rx.el.form(
                    rx.el.input(
                        name="request",
                        id="ai-request",
                        auto_complete="off",
                        placeholder=rx.cond(
                            AiState.status == "done",
                            "What should change in this answer?",
                            rx.cond(AiState.selected != "", "What should the AI do with this text?", "What should the AI write here?"),
                        ),
                        class_name="flex-1 min-w-0 px-3 py-1.5 text-sm border border-gray-300 rounded-md outline-none focus:border-violet-500",
                    ),
                    rx.el.button(
                        rx.icon("arrow-up", class_name="h-4 w-4"),
                        type="submit",
                        disabled=AiState.status == "writing",
                        title="Send (Enter)",
                        id="ai-send",
                        class_name="p-2 text-white bg-violet-600 rounded-md hover:bg-violet-700 disabled:opacity-40 transition-colors",
                    ),
                    on_submit=AiState.ask,
                    reset_on_submit=True,
                    class_name="flex items-center gap-2",
                ),
                rx.cond(
                    (AiState.status == "ready") | (AiState.status == "error"),
                    rx.cond(AiState.selected != "", _quick_row(ai.ON_SELECTION), _quick_row(ai.AT_CARET)),
                ),
                rx.cond(AiState.status != "ready", _actions()),
                id="ai-writer",
                style={"position": "fixed", "top": "30%", "left": "25%", "width": "640px", "maxWidth": "calc(100vw - 16px)", "zIndex": "40"},
                class_name="flex flex-col gap-2 p-3 bg-white border border-violet-200 rounded-lg shadow-xl",
            ),
        ),
    )


def ai_change_bar() -> rx.Component:
    """What the assistant changed in this document, with the button that takes it back: for
    everyone on it, as anyone there could change it by hand. Ctrl+Z doesn't reach it, because to the
    editor it is someone else's edit. Above the assistant's dialog, which stays open while it
    works."""
    if not AVAILABLE:
        return rx.fragment()

    def note(n: rx.Var) -> rx.Component:
        return rx.el.div(
            rx.icon("sparkles", class_name="h-4 w-4 text-violet-600 shrink-0"),
            rx.el.span(n["who"].to(str), ": ", n["summary"].to(str), class_name="ai-note-text text-xs text-gray-800 truncate"),
            rx.el.button(
                "Undo",
                on_click=AiState.undo_change(n["id"].to(str)),
                title="Take this change back",
                class_name="ai-note-undo shrink-0 px-2 py-1 text-xs font-medium text-violet-700 bg-violet-50 rounded hover:bg-violet-100 transition-colors",
            ),
            rx.el.button(
                rx.icon("x", class_name="h-3.5 w-3.5"),
                on_click=EditorState.close_ai_note(n["id"].to(str)),
                title="Dismiss",
                class_name="ai-note-close shrink-0 p-1 rounded text-gray-400 hover:bg-gray-100",
            ),
            class_name="ai-note flex items-center gap-2 max-w-[min(460px,calc(100vw-24px))] bg-white border border-violet-200 rounded-lg shadow-lg pl-3 pr-1.5 py-1.5",
        )

    return rx.el.div(rx.foreach(EditorState.ai_notes, note), class_name="flex flex-col items-start gap-2 fixed left-3 bottom-3", style={"zIndex": "1001"})
