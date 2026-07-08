"""WebSocket Connection Hub for client communication and broadcasting."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any
from fastapi import WebSocket


class WSHub:
    """Manages active WebSocket connections per session.

    Handles connection registration, removal, and message broadcasting.
    """

    def __init__(self) -> None:
        # session_id -> set of WebSocket connections
        self._connections: dict[str, set[WebSocket]] = defaultdict(set)
        self._lock: asyncio.Lock = asyncio.Lock()

    async def connect(self, session_id: str, ws: WebSocket) -> None:
        """Accept the WebSocket connection and register it.

        Args:
            session_id: The ID of the session.
            ws: The WebSocket connection instance.
        """
        await ws.accept()
        async with self._lock:
            self._connections[session_id].add(ws)

    async def disconnect(self, session_id: str, ws: WebSocket) -> None:
        """Discard the WebSocket connection and clean up empty sessions.

        Args:
            session_id: The ID of the session.
            ws: The WebSocket connection instance.
        """
        async with self._lock:
            self._connections[session_id].discard(ws)
            if not self._connections[session_id]:
                del self._connections[session_id]

    async def broadcast(self, session_id: str, event: dict[str, Any]) -> None:
        """Send event to ALL connections for this session.

        Dead connections are identified and removed silently.

        Args:
            session_id: The ID of the session.
            event: The dictionary event payload to send.
        """
        # Copy to avoid modifying set during iteration if exceptions trigger disconnects
        async with self._lock:
            connections = list(self._connections.get(session_id, set()))

        dead: set[WebSocket] = set()
        for ws in connections:
            try:
                await ws.send_json(event)
            except Exception:
                dead.add(ws)

        # Clean up dead connections
        for ws in dead:
            await self.disconnect(session_id, ws)

    async def send_stream(self, session_id: str, delta: str) -> None:
        """Broadcast a stream event with the given delta string.

        Args:
            session_id: The ID of the session.
            delta: The text fragment of the response.
        """
        await self.broadcast(
            session_id,
            {
                "type": "stream",
                "session_id": session_id,
                "payload": {"delta": delta},
            },
        )

    async def send_planning(self, session_id: str, status: str) -> None:
        """Broadcast a planning event with the status.

        Args:
            session_id: The ID of the session.
            status: The planning status string.
        """
        await self.broadcast(
            session_id,
            {
                "type": "planning",
                "session_id": session_id,
                "payload": {"status": status},
            },
        )

    async def send_done(self, session_id: str, usage: dict[str, int]) -> None:
        """Broadcast a done event with usage stats.

        Args:
            session_id: The ID of the session.
            usage: Dict containing token usage statistics.
        """
        await self.broadcast(
            session_id,
            {
                "type": "done",
                "session_id": session_id,
                "payload": {"usage": usage},
            },
        )

    async def send_error(self, session_id: str, message: str) -> None:
        """Broadcast an error event with the error message.

        Args:
            session_id: The ID of the session.
            message: The error message details.
        """
        await self.broadcast(
            session_id,
            {
                "type": "error",
                "session_id": session_id,
                "payload": {"message": message},
            },
        )

    async def send_swarm_start(self, session_id: str, total_steps: int, batches: list[list[int]]) -> None:
        """Broadcast a swarm_start event.

        Args:
            session_id: The ID of the session.
            total_steps: The total number of steps in the plan.
            batches: The batches containing step indices.
        """
        await self.broadcast(
            session_id,
            {
                "type": "swarm_start",
                "session_id": session_id,
                "payload": {"total_steps": total_steps, "batches": batches},
            },
        )

    async def send_worker_start(self, session_id: str, step_index: int, description: str) -> None:
        """Broadcast a worker_start event.

        Args:
            session_id: The ID of the session.
            step_index: The index of the plan step.
            description: The description of the step.
        """
        await self.broadcast(
            session_id,
            {
                "type": "worker_start",
                "session_id": session_id,
                "payload": {"step_index": step_index, "description": description},
            },
        )

    async def send_worker_done(self, session_id: str, step_index: int, result_preview: str) -> None:
        """Broadcast a worker_done event.

        Args:
            session_id: The ID of the session.
            step_index: The index of the plan step.
            result_preview: First 100 characters of the result + "..." if longer.
        """
        await self.broadcast(
            session_id,
            {
                "type": "worker_done",
                "session_id": session_id,
                "payload": {"step_index": step_index, "result_preview": result_preview},
            },
        )


# Singleton — one hub per process
ws_hub: WSHub = WSHub()
