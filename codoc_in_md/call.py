"""Calls on a document, carried out by a call app through the DDNS Intent `call.join`.

codoc keeps who is in each document's call and rings the people viewing it; the
call itself runs in the call app, opened in the intent dialog:

    Intent.start(None, "call.join", private={"room": <call id>}, keep_alive=True, single=True,
                 title=..., user=..., name=...)

- Anyone viewing a document can call everyone on it: the others get an incoming
  call (Accept / Decline) for RING_SECONDS.
- While the call is on, everyone on the document (also people who open it
  later) sees "Join call" with the number of people in it.
- The call dialog is keep-alive (other dialogs minimize it to the tray) and
  single (joining another call closes it).

The call app is whichever installed app provides `call.join` (the DDNS Intent
registry; `DDNS_INTENT_PROVIDER_CALL_JOIN` for local dev), unless
`CODOC_CALL_APP` names one. The call id is private: anyone holding it can join
the call, so it stays out of the iframe URL.

Like presence (`state.SharedState`), calls live in this process's memory.
"""

import os
import secrets
import time
from typing import TypedDict

import reflex as rx

try:
    from reflex_ddns_auth.intent import Intent, IntentState
    CALLS_ENABLED = True
except ImportError:
    CALLS_ENABLED = False

CALL_APP = os.environ.get("CODOC_CALL_APP") or None
CALL_ACTION = "call.join"
# How long a new call rings the people on the document.
RING_SECONDS = 45
# A tab in a call refreshes its entry this often...
TOUCH_SECONDS = 15
# ...and is dropped after this long without a heartbeat (closed tab, lost network).
# Generous because background tabs get their timers throttled.
STALE_SECONDS = 150
# The dialog opens one event after join_call; don't mistake that gap for a closed dialog.
OPENING_GRACE_SECONDS = 10


class Member(TypedDict):
    id: str
    name: str


class DocCall(TypedDict):
    call_id: str
    started_by_name: str
    started_at: float
    ringing: bool
    # Client token -> who; a person may be in the call from several tabs.
    members: dict[str, Member]
    last_seen: dict[str, float]
    # User ids who joined or declined: they are not rung (again).
    responded: list[str]


class CallStore:
    """The call of each document, at most one."""

    calls: dict[str, DocCall] = {}

    @classmethod
    def cleanup(cls, doc_id: str, now: float) -> None:
        """Drop members gone silent, stop ringing after RING_SECONDS, end an empty call."""
        call = cls.calls.get(doc_id)
        if call is None:
            return
        for token, seen in list(call["last_seen"].items()):
            if now - seen > STALE_SECONDS:
                call["members"].pop(token, None)
                call["last_seen"].pop(token, None)
        if call["ringing"] and now - call["started_at"] > RING_SECONDS:
            call["ringing"] = False
        if not call["members"]:
            del cls.calls[doc_id]

    @classmethod
    def join(cls, doc_id: str, token: str, member: Member, now: float, call_id: str = "") -> DocCall:
        """Join the document's call, starting it (ringing everyone) if there is none."""
        call = cls.calls.get(doc_id)
        if call is None:
            call = DocCall(
                call_id=call_id or secrets.token_urlsafe(12),
                started_by_name=member["name"],
                started_at=now,
                # A call put back after being dropped (call_id given) doesn't ring again.
                ringing=not call_id,
                members={},
                last_seen={},
                responded=[],
            )
            cls.calls[doc_id] = call
        call["members"][token] = member
        call["last_seen"][token] = now
        if member["id"] not in call["responded"]:
            call["responded"].append(member["id"])
        return call

    @classmethod
    def leave(cls, doc_id: str, token: str) -> None:
        """Take a tab out of the document's call; the call ends with its last member."""
        call = cls.calls.get(doc_id)
        if call is None:
            return
        call["members"].pop(token, None)
        call["last_seen"].pop(token, None)
        if not call["members"]:
            del cls.calls[doc_id]

    @classmethod
    def decline(cls, doc_id: str, user_id: str) -> None:
        call = cls.calls.get(doc_id)
        if call is not None and user_id not in call["responded"]:
            call["responded"].append(user_id)


class CallState(rx.State):
    """This tab's side of document calls."""

    # Document whose call this tab is in ("" when in no call).
    current_doc: str = ""
    # The call of the document on screen: how many are in it, and who is ringing us.
    call_count: int = 0
    ringing_from: str = ""
    _call_id: str = ""
    _joined_at: float = 0.0

    async def _me(self) -> tuple[str, str, str]:
        """(document on screen, user id, display name) of this tab."""
        from codoc_in_md.state import EditorState

        editor = await self.get_state(EditorState)
        name = editor.my_user_name if editor.is_authenticated else f"Guest {editor.my_user_id}"
        return editor.doc_id, editor.my_user_id, name

    def _refresh(self, doc_id: str, user_id: str) -> None:
        """Update what the header and the incoming-call popup show for ``doc_id``.

        Called by EditorState's presence loop, so changes made from other tabs
        show up within a moment.
        """
        CallStore.cleanup(doc_id, time.time())
        call = CallStore.calls.get(doc_id)
        count = len(call["members"]) if call else 0
        in_call = call is not None and any(m["id"] == user_id for m in call["members"].values())
        rung = call is not None and call["ringing"] and not in_call and user_id not in call["responded"]
        ringing_from = call["started_by_name"] if rung else ""
        # Only write what changed: this runs twice a second for every viewer.
        if self.call_count != count:
            self.call_count = count
        if self.ringing_from != ringing_from:
            self.ringing_from = ringing_from

    @rx.event
    async def join_call(self):
        """Call everyone on the document, or join its call, and open it in the dialog."""
        if not CALLS_ENABLED:
            return
        doc_id, user_id, name = await self._me()
        if not doc_id:
            return
        dialog = await self.get_state(IntentState)
        if self.current_doc == doc_id and CALL_ACTION in dialog.open_actions:
            # Already in this call (maybe minimized): bring it back rather than rejoin.
            return Intent.show(CALL_ACTION)

        now = time.time()
        token = self.router.session.client_token
        if self.current_doc and self.current_doc != doc_id:
            # Switching calls: the old dialog's on_cancel comes too late to know which one.
            CallStore.leave(self.current_doc, token)
        call = CallStore.join(doc_id, token, Member(id=user_id, name=name), now)
        self.current_doc = doc_id
        self._call_id = call["call_id"]
        self._joined_at = now
        self._refresh(doc_id, user_id)

        from codoc_in_md.state import DOCUMENTS_STORE

        doc = DOCUMENTS_STORE.get(doc_id)
        title = doc["title"] if doc else doc_id
        return Intent.start(
            CALL_APP,
            CALL_ACTION,
            on_result=CallState.call_closed,
            on_cancel=CallState.call_closed,
            private={"room": call["call_id"]},
            keep_alive=True,
            single=True,
            label=f"Call · {title}",
            title=title,
            user=user_id,
            name=name,
        )

    @rx.event
    async def decline_call(self):
        doc_id, user_id, _ = await self._me()
        CallStore.decline(doc_id, user_id)
        self._refresh(doc_id, user_id)

    @rx.event
    async def call_closed(self, data: dict):
        """The call dialog closed (hung up or closed): leave the call.

        Other dialogs only minimize it (keep-alive), so being replaced means
        another call took its place (single): join_call already moved us.
        """
        if data.get("reason") == "replaced" and data.get("by") == CALL_ACTION:
            return
        doc_id = self.current_doc
        self.current_doc = ""
        self._call_id = ""
        if doc_id:
            CallStore.leave(doc_id, self.router.session.client_token)
        on_screen, user_id, _ = await self._me()
        self._refresh(on_screen, user_id)

    @rx.event
    async def heartbeat(self):
        """Keep this tab in its call while the call dialog runs (in front or minimized)."""
        if not CALLS_ENABLED or not self.current_doc:
            return
        now = time.time()
        token = self.router.session.client_token
        doc_id = self.current_doc
        dialog = await self.get_state(IntentState)
        if CALL_ACTION not in dialog.open_actions and now - self._joined_at > OPENING_GRACE_SECONDS:
            # The dialog went away without telling us: we are not in the call.
            CallStore.leave(doc_id, token)
            self.current_doc = ""
            self._call_id = ""
            return

        CallStore.cleanup(doc_id, now)
        call = CallStore.calls.get(doc_id)
        if call is not None and call["call_id"] != self._call_id:
            # Another call took this document's place while ours was dropped.
            self.current_doc = ""
            self._call_id = ""
            return
        if call is None or token not in call["members"] or now - call["last_seen"][token] > TOUCH_SECONDS:
            # Touch our entry, or put the call back if it was dropped (e.g. this tab
            # slept past STALE_SECONDS) while the dialog still runs it.
            _, user_id, name = await self._me()
            CallStore.join(doc_id, token, Member(id=user_id, name=name), now, call_id=self._call_id)
