"""Simple WebSocket relay for Yjs sync protocol.

Each document room is identified by ``doc_id`` in the URL path.  The relay
forwards *all* binary messages from one client to every other client in the
same room.  It does **not** interpret the Yjs protocol – the y-websocket
client library handles sync-step-1/step-2/update/awareness negotiation
peer-to-peer via the relay.

The one thing it does read is which awareness clients (cursor, name, color)
each connection announces, so that when the connection goes away it can tell
the room those clients left, as y-websocket's own server does.  A closing
tab's own goodbye is not always sent (mobile browsers often skip unload
handlers); without this, a departed person's cursor would linger until the
y-protocols awareness timeout (30 s, or longer in a throttled background tab).

The text lives in the browsers, so a change from the server (the AI's) comes in the way a tab's
does: a :class:`Visitor` joins the room for a moment, gets the text from the tabs there, and sends
its change to them. It reaches everyone like someone's typing and merges with what they type at
that moment. Holding no text here also means a restart of the server can't bring a second copy of
a document to meet the one in an open tab.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections import defaultdict
from typing import Iterable, Optional, Tuple

from pycrdt import Doc, Text, YMessageType, YSyncMessageType, create_sync_message, create_update_message, handle_sync_message
from starlette.routing import WebSocketRoute
from starlette.websockets import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

# Room name → set of connected WebSocket instances.
_rooms: dict[str, set[WebSocket]] = defaultdict(set)
# WebSocket → awareness clientID → the latest clock it announced for it.
_awareness_clients: dict[WebSocket, dict[int, int]] = {}

# y-websocket message types.
MESSAGE_AWARENESS = 1

# The Y.Text the browsers bind their editor to (assets/yjs_collab.js).
TEXT_NAME = "monaco"
# How long the tabs in a room get to hand a visitor the text.
JOIN_TIMEOUT = 4.0
# After the first tab answered: the others' answers come in with whatever it hadn't got yet.
JOIN_SETTLE = 0.1


def _read_varuint(data: bytes, pos: int) -> tuple[int, int]:
    """Read a lib0 variable-length unsigned int (7 bits per byte, little-endian)."""
    value = 0
    shift = 0
    while True:
        if pos >= len(data) or shift > 63:
            raise ValueError("bad varuint")
        byte = data[pos]
        pos += 1
        value |= (byte & 0x7F) << shift
        if byte < 0x80:
            return value, pos
        shift += 7


def _write_varuint(value: int) -> bytes:
    out = bytearray()
    while value > 0x7F:
        out.append(0x80 | (value & 0x7F))
        value >>= 7
    out.append(value)
    return bytes(out)


def _awareness_clients_in(data: bytes) -> dict[int, tuple[int, bool]]:
    """clientID → (clock, still here) for an awareness message; {} for any other."""
    try:
        msg_type, pos = _read_varuint(data, 0)
        if msg_type != MESSAGE_AWARENESS:
            return {}
        length, pos = _read_varuint(data, pos)
        end = pos + length
        count, pos = _read_varuint(data, pos)
        clients: dict[int, tuple[int, bool]] = {}
        for _ in range(count):
            client_id, pos = _read_varuint(data, pos)
            clock, pos = _read_varuint(data, pos)
            state_len, pos = _read_varuint(data, pos)
            state = data[pos : pos + state_len]
            pos += state_len
            if pos > end:
                raise ValueError("truncated awareness update")
            clients[client_id] = (clock, state != b"null")
        return clients
    except (ValueError, IndexError):
        return {}


def _awareness_goodbye(clients: dict[int, int]) -> bytes:
    """An awareness update saying these clients left: state null, clock + 1."""
    payload = bytearray(_write_varuint(len(clients)))
    for client_id, clock in clients.items():
        payload += _write_varuint(client_id) + _write_varuint(clock + 1)
        payload += _write_varuint(4) + b"null"
    return _write_varuint(MESSAGE_AWARENESS) + _write_varuint(len(payload)) + bytes(payload)


def _awareness_update(client_id: int, clock: int, state: dict) -> bytes:
    """An awareness update saying what this client shows the others (its name, its selection)."""
    body = json.dumps(state).encode("utf-8")
    payload = _write_varuint(1) + _write_varuint(client_id) + _write_varuint(clock)
    payload += _write_varuint(len(body)) + body
    return _write_varuint(MESSAGE_AWARENESS) + _write_varuint(len(payload)) + payload


async def _broadcast(room: set[WebSocket], sender: WebSocket | None, data: bytes) -> None:
    """Send ``data`` to every client in the room except ``sender``.

    Iterates over a snapshot: a client can join or leave (changing the set)
    while a send is awaited.  Iterating the live set raised "Set changed size
    during iteration", which closed the sender's connection and left the
    message half-delivered.
    """
    stale: set[WebSocket] = set()
    for peer in list(room):
        if peer is sender:
            continue
        try:
            await peer.send_bytes(data)
        except Exception:
            stale.add(peer)
    if stale:
        room -= stale


async def _yjs_ws_endpoint(websocket: WebSocket) -> None:
    """Handle a single Yjs WebSocket connection."""

    doc_id: str = websocket.path_params.get("doc_id", "")
    if not doc_id:
        await websocket.close(code=4000, reason="Missing doc_id")
        return

    await websocket.accept()
    room = _rooms[doc_id]
    room.add(websocket)
    announced = _awareness_clients.setdefault(websocket, {})
    logger.info("yjs-ws: +1 in room %s (%d total)", doc_id, len(room))

    try:
        while True:
            data: bytes = await websocket.receive_bytes()
            for client_id, (clock, here) in _awareness_clients_in(data).items():
                if here:
                    announced[client_id] = clock
                else:
                    announced.pop(client_id, None)  # said goodbye itself
            await _broadcast(room, websocket, data)
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.warning("yjs-ws: error in room %s: %s", doc_id, exc)
    finally:
        room.discard(websocket)
        left = _awareness_clients.pop(websocket, {})
        if left and room:
            try:
                await _broadcast(room, None, _awareness_goodbye(left))
            except Exception as exc:
                logger.warning("yjs-ws: goodbye in room %s failed: %s", doc_id, exc)
        remaining = len(_rooms.get(doc_id, set()))
        if remaining == 0:
            _rooms.pop(doc_id, None)
        logger.info("yjs-ws: -1 in room %s (%d remaining)", doc_id, remaining)


def _units(text: str) -> int:
    """How long ``text`` is to Yjs, which counts in UTF-16 units (an emoji is 2)."""
    return len(text.encode("utf-16-le")) // 2


class Visitor:
    """The server in a document's room for a moment, as one more peer of the tabs.

    It sits in the room's set of sockets (the relay only ever calls ``send_bytes``), so it hears
    what everyone hears. Made by :func:`visit`.
    """

    def __init__(self, doc_id: str) -> None:
        self.doc_id = doc_id
        self.doc = Doc()
        self.text = self.doc.get(TEXT_NAME, type=Text)
        self._heard = asyncio.Event()
        self._clock = 0  # how much text it has written: the Yjs ids of what it writes next
        self._aware_clock = 0
        self._user: dict = {}
        self._mark: Optional[dict] = None
        self._leaving: Optional[asyncio.Task] = None

    @property
    def value(self) -> str:
        return str(self.text)

    async def send_bytes(self, data: bytes) -> None:
        """A message of the room. Only the document matters here: an answer with its text, or a
        change someone makes while the visitor is here."""
        if data[:1] != bytes([YMessageType.SYNC]) or data[1:2] == bytes([YSyncMessageType.SYNC_STEP1]):
            return
        try:
            handle_sync_message(data[1:], self.doc)
        except Exception as exc:  # noqa: BLE001 – a message it can't read changes nothing
            logger.warning("yjs-ws: visitor in room %s: %s", self.doc_id, exc)
            return
        self._heard.set()

    async def _send(self, data: bytes) -> None:
        room = _rooms.get(self.doc_id)
        if room is not None:
            await _broadcast(room, self, data)

    async def _ask_for_text(self, wanted: bool) -> None:
        """Gets the text from the tabs. With ``wanted``, a tab that has no text yet doesn't count
        as an answer (it has only just connected, and is about to get it or to start it)."""
        await self._send(create_sync_message(self.doc))
        deadline = time.monotonic() + JOIN_TIMEOUT
        while True:
            left = deadline - time.monotonic()
            if left <= 0:
                raise TimeoutError(f"the tabs on document {self.doc_id} didn't answer")
            try:
                await asyncio.wait_for(self._heard.wait(), left)
            except asyncio.TimeoutError:
                continue
            self._heard.clear()
            if self.value or not wanted:
                break
        await asyncio.sleep(JOIN_SETTLE)

    async def show_as(self, name: str, color: str) -> None:
        """Who it is for the people in the room: its name and color on what it marks."""
        self._user = {"name": name, "color": color}
        await self._say({"user": self._user})

    async def _say(self, state: dict) -> None:
        self._aware_clock += 1
        await self._send(_awareness_update(self.doc.client_id, self._aware_clock, state))

    async def replace(self, pieces: Iterable[Tuple[int, int, str]]) -> None:
        """Makes these changes, ``(start, end, new text)`` in ``value`` and apart from each other,
        in one go, and marks the first for the people in the room, as a selection in the visitor's
        color."""
        value = self.value
        before = self.doc.get_state()
        spots = []
        with self.doc.transaction():
            for start, end, new in sorted(pieces, reverse=True):
                # pycrdt counts text positions in UTF-8 bytes, Python in characters.
                at = len(value[:start].encode("utf-8"))
                gone = len(value[start:end].encode("utf-8"))
                if gone:
                    del self.text[at : at + gone]
                if new:
                    self.text.insert(at, new)
                    spots.append((self._clock, self._clock + _units(new) - 1))
                    self._clock += _units(new)
        await self._send(create_update_message(self.doc.get_update(before)))
        if spots:
            first, last = spots[-1]  # written last, it is the first in the text
            await self._say({"user": self._user, "selection": {"anchor": self._position(first, 0), "head": self._position(last, -1)}})

    def _position(self, clock: int, assoc: int) -> dict:
        """A Yjs relative position on what the visitor wrote, as tabs publish theirs: just before
        that unit of text (``assoc`` 0), or just after it (-1)."""
        return {"item": {"client": self.doc.client_id, "clock": clock}, "assoc": assoc}

    async def _leave(self, after: float) -> None:
        await asyncio.sleep(after)
        room = _rooms.get(self.doc_id)
        if room is None:
            return
        if self._aware_clock:
            await _broadcast(room, self, _awareness_goodbye({self.doc.client_id: self._aware_clock}))
        room.discard(self)
        if not room:
            _rooms.pop(self.doc_id, None)

    def leave(self, after: float = 0.0) -> None:
        """Leaves the room ``after`` these seconds; until then what it marked stays marked."""
        if self._leaving is None:
            self._leaving = asyncio.create_task(self._leave(after))


def has_tabs(doc_id: str) -> bool:
    """Whether a browser is connected to the document's room."""
    return any(isinstance(peer, WebSocket) for peer in _rooms.get(doc_id, ()))


async def visit(doc_id: str, *, wanted: bool = True) -> Optional[Visitor]:
    """Joins the document's room: a :class:`Visitor` holding the text as the tabs have it (it must
    ``leave``), or None when no tab is there and the saved document is all there is. ``wanted``
    says the document has text, so that a tab with none yet is waited for; raises TimeoutError
    when the tabs don't hand it over."""
    if not has_tabs(doc_id):
        return None
    visitor = Visitor(doc_id)
    _rooms[doc_id].add(visitor)
    try:
        await visitor._ask_for_text(wanted)
    except BaseException:
        visitor.leave()
        raise
    return visitor


def register_yjs_routes(app) -> None:  # noqa: ANN001 – Reflex App
    """Register the ``/yjs/{doc_id}`` WebSocket endpoint on the backend."""

    existing = {getattr(r, "path", None) for r in getattr(app._api, "routes", [])}
    if "/yjs/{doc_id}" not in existing:
        app._api.routes.append(WebSocketRoute("/yjs/{doc_id}", _yjs_ws_endpoint))
