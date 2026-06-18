"""API router — all HTTP endpoints live here.

This module follows the architecture defined in ``docs/ARCHITECTURE.md``:

    | Router | app/api/router.py | All HTTP endpoints |
"""

from __future__ import annotations

import asyncio
import uuid
from collections import defaultdict
from time import time

from fastapi import APIRouter, Depends, HTTPException, Request, WebSocket, WebSocketDisconnect

from pydantic import BaseModel

from app.core.ws_hub import ws_hub
from app.core.auth import verify_ws_token, decode_token, create_access_token, get_current_user_id
from app.core.session import SessionManager, session_manager as singleton_session_manager
from app.memory.chroma import list_memories, delete_memory


router = APIRouter()

_token_requests: dict[str, list[float]] = defaultdict(list)


def get_session_manager() -> SessionManager:
    """Dependency provider for the singleton SessionManager."""
    return singleton_session_manager


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Return a simple health-check response.

    Returns:
        A dictionary with a single ``status`` key.
    """
    return {"status": "ok"}


@router.post("/auth/token")
async def issue_token(request: Request) -> dict[str, str]:
    """Issue an anonymous JWT for Phase 1 MVP.

    Rate limited to 5 requests per minute per IP to prevent abuse.
    This is a temporary Phase 1 measure — see docs/DECISIONS.md ADR-010.

    Args:
        request: The incoming HTTP request (used for client IP extraction).

    Returns:
        A dictionary with an ``access_token`` key.

    Raises:
        HTTPException: 429 if the client exceeds 5 requests per minute.
    """
    client_ip = request.client.host if request.client else "unknown"
    now = time()
    _token_requests[client_ip] = [
        t for t in _token_requests[client_ip] if now - t < 60
    ]
    if len(_token_requests[client_ip]) >= 5:
        raise HTTPException(status_code=429, detail="Too many token requests")
    _token_requests[client_ip].append(now)

    anonymous_user_id = f"anon-{uuid.uuid4()}"
    token = create_access_token(anonymous_user_id)
    return {"access_token": token}


@router.websocket("/ws/{session_id}")
async def websocket_endpoint(
    session_id: str,
    websocket: WebSocket,
    session_manager: SessionManager = Depends(get_session_manager),
) -> None:
    """WebSocket endpoint for real-time agent interaction.

    Args:
        session_id: The ID of the session.
        websocket: The WebSocket connection object.
        session_manager: The injected SessionManager instance.
    """
    token = websocket.query_params.get("token")
    payload = decode_token(token) if token else None
    if payload is None:
        await websocket.close(code=4001, reason="Unauthorized")
        return
    user_id = str(payload.get("sub", "default_user"))

    await ws_hub.connect(session_id, websocket)
    session_manager.get_or_create(session_id, user_id)
    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})
            elif msg_type == "task":
                # TODO(phase-2): store task reference to prevent GC and enable cancellation
                asyncio.create_task(
                    session_manager.handle_task(session_id, data.get("payload", {}))
                )
            elif msg_type == "cancel":
                await session_manager.cancel(session_id)
    except WebSocketDisconnect:
        pass
    finally:
        await ws_hub.disconnect(session_id, websocket)


class MemoryEntry(BaseModel):
    id: str
    content: str
    role: str
    session_id: str
    timestamp: str


class MemoryListResponse(BaseModel):
    memories: list[MemoryEntry]


@router.get("/memory", response_model=MemoryListResponse)
async def get_memories(user_id: str = Depends(get_current_user_id)) -> MemoryListResponse:
    entries = await list_memories(user_id)
    return MemoryListResponse(memories=[MemoryEntry(**e) for e in entries])


@router.delete("/memory/{memory_id}")
async def remove_memory(
    memory_id: str,
    user_id: str = Depends(get_current_user_id),
) -> dict[str, bool]:
    deleted = await delete_memory(user_id, memory_id)
    if not deleted:
        # 404, not 403 — do not confirm to an unauthorized caller
        # that a memory with this ID exists at all.
        raise HTTPException(status_code=404, detail="Memory not found")
    return {"deleted": True}

