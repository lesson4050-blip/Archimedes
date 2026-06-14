"""API router — all HTTP endpoints live here.

This module follows the architecture defined in ``docs/ARCHITECTURE.md``:

    | Router | app/api/router.py | All HTTP endpoints |
"""

from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
import asyncio

from app.core.ws_hub import ws_hub
from app.core.auth import verify_ws_token
from app.core.session import SessionManager, session_manager as singleton_session_manager

router = APIRouter()


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
    if not verify_ws_token(token):
        await websocket.close(code=4001, reason="Unauthorized")
        return

    user_id = "default_user"
    if token:
        try:
            from jose import jwt  # type: ignore[import-untyped]
            from app.core.config import get_settings
            settings = get_settings()
            payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
            user_id = payload.get("sub", "default_user")
        except Exception:
            pass

    await ws_hub.connect(session_id, websocket)
    session_manager.get_or_create(session_id, user_id)
    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})
            elif msg_type == "task":
                asyncio.create_task(
                    session_manager.handle_task(session_id, data.get("payload", {}))
                )
            elif msg_type == "cancel":
                await session_manager.cancel(session_id)
    except WebSocketDisconnect:
        pass
    finally:
        await ws_hub.disconnect(session_id, websocket)
