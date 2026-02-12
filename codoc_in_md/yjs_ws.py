"""Simple WebSocket relay for Yjs sync protocol.

Each document room is identified by ``doc_id`` in the URL path.  The relay
forwards *all* binary messages from one client to every other client in the
same room.  It does **not** interpret the Yjs protocol – the y-websocket
client library handles sync-step-1/step-2/update/awareness negotiation
peer-to-peer via the relay.
"""

from __future__ import annotations

import logging
from collections import defaultdict

from starlette.websockets import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

# Room name → set of connected WebSocket instances.
_rooms: dict[str, set[WebSocket]] = defaultdict(set)


async def _yjs_ws_endpoint(websocket: WebSocket) -> None:
    """Handle a single Yjs WebSocket connection."""

    doc_id: str = websocket.path_params.get("doc_id", "")
    if not doc_id:
        await websocket.close(code=4000, reason="Missing doc_id")
        return

    await websocket.accept()
    room = _rooms[doc_id]
    room.add(websocket)
    logger.info("yjs-ws: +1 in room %s (%d total)", doc_id, len(room))

    try:
        while True:
            data: bytes = await websocket.receive_bytes()

            # Broadcast to every *other* client in the room.
            stale: set[WebSocket] = set()
            for peer in room:
                if peer is websocket:
                    continue
                try:
                    await peer.send_bytes(data)
                except Exception:
                    stale.add(peer)
            if stale:
                room -= stale
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.warning("yjs-ws: error in room %s: %s", doc_id, exc)
    finally:
        room.discard(websocket)
        remaining = len(_rooms.get(doc_id, set()))
        if remaining == 0:
            _rooms.pop(doc_id, None)
        logger.info("yjs-ws: -1 in room %s (%d remaining)", doc_id, remaining)


def register_yjs_routes(app) -> None:  # noqa: ANN001 – Reflex App
    """Register the ``/yjs/{doc_id}`` WebSocket endpoint on the backend."""

    existing = {getattr(r, "path", None) for r in getattr(app._api, "routes", [])}
    if "/yjs/{doc_id}" not in existing:
        app._api.add_websocket_route("/yjs/{doc_id}", _yjs_ws_endpoint)
