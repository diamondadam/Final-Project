from __future__ import annotations

import asyncio

from fastapi import WebSocket
from fastapi.websockets import WebSocketState


class WebSocketManager:
    """
    Maintains the set of active Unreal Engine WebSocket connections.

    broadcast() serialises TwinStateResponse to JSON and fans out to every
    connected client. Stale or closed connections are pruned automatically
    so a disconnected Unreal client never stalls the broadcast.
    """

    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._connections.add(ws)

    async def disconnect(self, ws: WebSocket) -> None:
        async with self._lock:
            self._connections.discard(ws)

    async def broadcast(self, payload: dict) -> None:
        """Send JSON payload to all connected clients; prune dead connections."""
        dead: set[WebSocket] = set()

        async with self._lock:
            snapshot = set(self._connections)

        for ws in snapshot:
            try:
                if ws.client_state == WebSocketState.CONNECTED:
                    await ws.send_json(payload)
                else:
                    dead.add(ws)
            except Exception:
                dead.add(ws)

        if dead:
            async with self._lock:
                self._connections -= dead
