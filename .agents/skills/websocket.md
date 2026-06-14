# Skill: WebSocket + FastAPI

## Trigger
Use when working on WebSocket endpoints, real-time streaming, session management,
or anything in app/core/ws_hub.py, app/core/session.py, app/api/router.py.

---

## Our WebSocket Architecture

```
Client (any surface)
  └── ws://localhost:8000/ws/{session_id}?token=<jwt>
        └── WSHub (connection registry + broadcast)
              └── SessionManager (isolated per-user state)
                    └── Agent Engine (streams tokens back)
```

All WebSocket connections go through ONE hub. Never create standalone WS handlers.

---

## Message Protocol (follow exactly)

```python
# Inbound (client → server)
class WSMessage(BaseModel):
    type: Literal["task", "ping", "cancel"]
    session_id: str
    payload: dict[str, Any]

# Outbound (server → client)
class WSEvent(BaseModel):
    type: Literal["stream", "tool_call", "tool_result", "done", "error"]
    session_id: str
    payload: dict[str, Any]
```

Never invent new message types without updating this protocol in ARCHITECTURE.md.

---

## WSHub Implementation Pattern

```python
# app/core/ws_hub.py
from fastapi import WebSocket
from collections import defaultdict
import asyncio

class WSHub:
    def __init__(self) -> None:
        # session_id -> set of WebSocket connections
        self._connections: dict[str, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, session_id: str, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._connections[session_id].add(ws)

    async def disconnect(self, session_id: str, ws: WebSocket) -> None:
        async with self._lock:
            self._connections[session_id].discard(ws)
            if not self._connections[session_id]:
                del self._connections[session_id]

    async def broadcast(self, session_id: str, event: dict[str, Any]) -> None:
        """Send event to ALL connections for this session."""
        dead: set[WebSocket] = set()
        for ws in self._connections.get(session_id, set()):
            try:
                await ws.send_json(event)
            except Exception:
                dead.add(ws)
        # Clean up dead connections
        for ws in dead:
            await self.disconnect(session_id, ws)

    async def send_stream(self, session_id: str, delta: str) -> None:
        await self.broadcast(session_id, {
            "type": "stream",
            "session_id": session_id,
            "payload": {"delta": delta},
        })

    async def send_done(self, session_id: str, usage: dict[str, int]) -> None:
        await self.broadcast(session_id, {
            "type": "done",
            "session_id": session_id,
            "payload": {"usage": usage},
        })

    async def send_error(self, session_id: str, message: str) -> None:
        await self.broadcast(session_id, {
            "type": "error",
            "session_id": session_id,
            "payload": {"message": message},
        })

# Singleton — one hub per process
ws_hub = WSHub()
```

---

## FastAPI WebSocket Endpoint Pattern

```python
# app/api/router.py
from fastapi import WebSocket, WebSocketDisconnect, Depends
from app.core.ws_hub import ws_hub
from app.core.auth import verify_ws_token
from app.core.session import SessionManager

@router.websocket("/ws/{session_id}")
async def websocket_endpoint(
    session_id: str,
    websocket: WebSocket,
    session_manager: SessionManager = Depends(),
) -> None:
    # 1. Auth before accepting
    token = websocket.query_params.get("token")
    if not verify_ws_token(token):
        await websocket.close(code=4001, reason="Unauthorized")
        return

    # 2. Register connection
    await ws_hub.connect(session_id, websocket)

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})

            elif msg_type == "task":
                # Run agent — stream results back via hub
                asyncio.create_task(
                    session_manager.handle_task(session_id, data["payload"])
                )

            elif msg_type == "cancel":
                await session_manager.cancel(session_id)

    except WebSocketDisconnect:
        pass
    finally:
        await ws_hub.disconnect(session_id, websocket)
```

---

## Session Manager Pattern

```python
# app/core/session.py
import uuid
from dataclasses import dataclass, field
from app.core.ws_hub import ws_hub

@dataclass
class Session:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    history: list[dict[str, str]] = field(default_factory=list)
    is_running: bool = False
    cancel_requested: bool = False

class SessionManager:
    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}

    def create(self, user_id: str) -> Session:
        session = Session(user_id=user_id)
        self._sessions[session.id] = session
        return session

    def get(self, session_id: str) -> Session | None:
        return self._sessions.get(session_id)

    def get_or_create(self, session_id: str, user_id: str) -> Session:
        if session_id not in self._sessions:
            session = Session(id=session_id, user_id=user_id)
            self._sessions[session_id] = session
        return self._sessions[session_id]

    async def cancel(self, session_id: str) -> None:
        session = self._sessions.get(session_id)
        if session:
            session.cancel_requested = True

    async def handle_task(self, session_id: str, payload: dict) -> None:
        session = self.get(session_id)
        if not session or session.is_running:
            return
        session.is_running = True
        session.cancel_requested = False
        try:
            # Will be replaced by real agent in Phase 2
            await ws_hub.send_stream(session_id, "Processing...")
            await ws_hub.send_done(session_id, {"prompt_tokens": 0, "completion_tokens": 0})
        except Exception as e:
            await ws_hub.send_error(session_id, str(e))
        finally:
            session.is_running = False
```

---

## Auth for WebSocket

```python
# app/core/auth.py
from jose import jwt, JWTError
from app.core.config import get_settings

def verify_ws_token(token: str | None) -> bool:
    """Validate JWT from WebSocket query param ?token=<jwt>."""
    if not token:
        return False
    try:
        settings = get_settings()
        jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        return True
    except JWTError:
        return False
```

---

## Testing WebSocket Endpoints

```python
# tests/integration/test_websocket.py
import pytest
from fastapi.testclient import TestClient
from app.main import create_app

@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())

def test_ws_rejects_missing_token(client: TestClient) -> None:
    with client.websocket_connect("/ws/test-session") as ws:
        # Should close with 4001
        pass  # WebSocketDisconnect raised — connection rejected

def test_ws_ping_pong(client: TestClient, valid_token: str) -> None:
    with client.websocket_connect(f"/ws/test-session?token={valid_token}") as ws:
        ws.send_json({"type": "ping", "session_id": "test-session", "payload": {}})
        data = ws.receive_json()
        assert data["type"] == "pong"

def test_ws_task_returns_stream_then_done(client: TestClient, valid_token: str) -> None:
    with client.websocket_connect(f"/ws/test-session?token={valid_token}") as ws:
        ws.send_json({
            "type": "task",
            "session_id": "test-session",
            "payload": {"message": "hello"}
        })
        events = [ws.receive_json() for _ in range(2)]
        types = [e["type"] for e in events]
        assert "stream" in types
        assert "done" in types
```

---

## Rules

- WSHub is a singleton — import `ws_hub` from `app.core.ws_hub`, never instantiate a new one
- Always authenticate BEFORE `ws.accept()` — reject with close code 4001
- Always wrap handler in try/finally to clean up disconnected clients
- Never block the event loop in a WS handler — use `asyncio.create_task` for agent work
- Dead connection cleanup must happen silently (catch all exceptions in broadcast)
- Session state lives in SessionManager, NOT in the WebSocket handler
