"""One tab's AI in the editor (``ai`` words the requests): the text it is writing for the selection
or the caret, which the person accepts or rejects. What they accept goes in as their own edit
(``assets/ai_writer.js``), so everyone gets it the way typing goes and Ctrl+Z takes it back.

A state of its own, so that an answer streaming in doesn't redraw what hangs on ``EditorState``.
"""

from __future__ import annotations

import json
import time
from typing import Any, Dict, List, TypedDict

import reflex as rx

from . import ai
from .state import EditorState

# How often an answer is shown as it grows.
STREAM_EVERY = 0.15
TALK_KEPT = 6  # earlier turns of a conversation about one piece of text
# Models that think first count their thinking in this too: a few hundred words took 4,000.
MIN_TOKENS = 8000
MAX_TOKENS = 16000


class Run(TypedDict):
    op: str  # same | gone | new
    text: str


class AiState(rx.State):
    writer_open: bool = False
    # ready: waits for the person's words. writing. done: the answer, to accept. error.
    status: str = "ready"
    # What the answer replaces ("": it goes in at the caret), and how that is called.
    selected: str = ""
    where: str = ""
    # The answer as it is written, the same as a change to the selection, and who wrote it.
    answer: str = ""
    runs: List[Run] = []
    model: str = ""
    error: str = ""
    _job: int = 0
    _around: Dict[str, str] = {}
    _talk: List[Dict[str, str]] = []
    _final: str = ""

    @rx.event
    def open_writer(self, info: Dict[str, Any]):
        """The person called the writer up on what ``assets/ai_writer.js`` took from the editor."""
        if not ai.ENABLED or not info:
            return
        self._job += 1
        self.writer_open = True
        self.status = "ready"
        self.selected = str(info.get("selected") or "")
        self.where = str(info.get("where") or "")
        self.answer = self.error = self._final = ""
        self.runs = []
        self._talk = []
        self._around = {k: str(info.get(k) or "") for k in ("before", "after", "title")}

    @rx.event
    def close_writer(self):
        """Reject, or Esc: nothing changes."""
        self._job += 1
        self.writer_open = False
        self.status = "ready"
        return rx.call_script("window.codocAi && window.codocAi.drop()")

    @rx.event
    def stop(self):
        """Stops the answer being written; the writer stays open for another try."""
        self._job += 1
        self.status = "ready"
        self.answer = ""
        self._talk = []

    async def _fail(self, seq: int, why: str) -> None:
        async with self:
            if self._job == seq:
                self.status = "error"
                self.error = why

    async def _write(self, request: str) -> None:
        """Asks for the text and shows it as it comes."""
        request = " ".join(request.split()) if request else ""
        if not request:
            return
        async with self:
            if self.status == "writing" or not self.writer_open:
                return
            self._job += 1
            seq = self._job
            self.status = "writing"
            self.answer = self.error = self._final = ""
            self.runs = []
            selected, before = self.selected, self._around["before"]
            if self._talk:
                messages = [*self._talk, {"role": "user", "content": f"{request}\n\nAnswer with the whole new text again, and nothing else."}]
            else:
                around = self._around
                messages = [{"role": "user", "content": ai.prompt(around["title"], around["before"], selected, around["after"], request)}]
            editor = await self.get_state(EditorState)
            user = editor.my_user_email or editor.my_user_name
        status = await ai.hub.status(ai.ROLE, user)
        if not status or not status.get("ok"):
            await self._fail(seq, str((status or {}).get("error") or "There is no AI Hub to ask."))
            return
        async with self:
            if self._job != seq:
                return
            self.model = str(status.get("model") or "")
        reply = ai.hub.stream(ai.ROLE, ai.SYSTEM, messages, max_tokens=min(MAX_TOKENS, max(MIN_TOKENS, 4 * len(selected))), effort="low", user=user)
        text = ""
        shown = 0.0
        try:
            async for piece in reply:
                text += piece
                if time.monotonic() - shown >= STREAM_EVERY:
                    async with self:
                        if self._job != seq:
                            return
                        self.answer = text
                    shown = time.monotonic()
        except ai.FAILED as ex:
            await self._fail(seq, str(ex))
            return
        if reply.stop == "refusal":
            await self._fail(seq, "The model declined this request.")
            return
        if reply.stop == "max_tokens":
            await self._fail(seq, "The answer was cut off: select less text, or choose a quicker model on the AI Hub's page.")
            return
        final = ai.cleaned(text, selected, before)
        if not final.strip():
            await self._fail(seq, "The AI gave no answer: ask again, or in other words.")
            return
        talk = [*messages, {"role": "assistant", "content": text}]
        async with self:
            if self._job != seq:
                return
            self._final = final
            self._talk = talk if len(talk) <= TALK_KEPT + 1 else talk[:1] + talk[-TALK_KEPT:]
            self.answer = final
            self.runs = ai.marks(selected, final)
            self.model = reply.model or self.model
            self.status = "done"

    @rx.event(background=True)
    async def ask(self, form: Dict[str, Any]):
        """The person's own words: what to do, or what to change in the answer on screen."""
        await self._write(str(form.get("request") or ""))

    @rx.event(background=True)
    async def quick(self, name: str):
        """One of the writer's buttons."""
        action = ai.ON_SELECTION.get(name) or ai.AT_CARET.get(name)
        if action:
            await self._write(action[1])

    @rx.event
    def accept(self, below: bool = False):
        """Puts the answer in the document: instead of the selection, or under it."""
        if self.status != "done" or not self._final:
            return None
        call = f"window.codocAi && window.codocAi.apply({json.dumps(self._final)}, {json.dumps(bool(below))})"
        return rx.call_script(call, callback=AiState.applied)

    @rx.event
    def applied(self, ok: Any):
        if ok:
            self._job += 1
            self.writer_open = False
            self.status = "ready"
        else:
            self.status = "error"
            self.error = "The text here changed while the AI was writing, so its answer wasn't put in."

    @rx.event(background=True)
    async def undo_change(self, change_id: str):
        """Takes back a change the assistant made to this document (the note about it)."""
        from . import ai_tools

        async with self:
            doc_id = (await self.get_state(EditorState)).doc_id
        why = await ai_tools.take_back(doc_id, change_id)
        if why:
            yield rx.toast.error(why, duration=6000, position="bottom-right")
