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
"""

from __future__ import annotations

import logging
from collections import defaultdict

from starlette.routing import WebSocketRoute
from starlette.websockets import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

# Room name → set of connected WebSocket instances.
_rooms: dict[str, set[WebSocket]] = defaultdict(set)
# WebSocket → awareness clientID → the latest clock it announced for it.
_awareness_clients: dict[WebSocket, dict[int, int]] = {}

# y-websocket message types.
MESSAGE_AWARENESS = 1


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


def register_yjs_routes(app) -> None:  # noqa: ANN001 – Reflex App
    """Register the ``/yjs/{doc_id}`` WebSocket endpoint on the backend."""

    existing = {getattr(r, "path", None) for r in getattr(app._api, "routes", [])}
    if "/yjs/{doc_id}" not in existing:
        app._api.routes.append(WebSocketRoute("/yjs/{doc_id}", _yjs_ws_endpoint))
