"""Integration tests for the WebSocket endpoint."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocketDisconnect


def test_ws_rejects_missing_token(client: TestClient) -> None:
    """The WebSocket connection must be rejected with close code 4001 when token is missing."""
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/ws/test-session") as _:
            pass
    assert exc_info.value.code == 4001


def test_ws_ping_pong(client: TestClient, valid_token: str) -> None:
    """The WebSocket must respond with a pong message when a ping is received."""
    with client.websocket_connect(f"/ws/test-session?token={valid_token}") as ws:
        ws.send_json({
            "type": "ping",
            "session_id": "test-session",
            "payload": {},
        })
        data = ws.receive_json()
        assert data["type"] == "pong"


def test_ws_task_streams_and_completes(client: TestClient, valid_token: str) -> None:
    """Sending a task through the WebSocket must stream the echo delta and complete with done."""
    with client.websocket_connect(f"/ws/test-session?token={valid_token}") as ws:
        ws.send_json({
            "type": "task",
            "session_id": "test-session",
            "payload": {"message": "hello"},
        })
        events = [ws.receive_json() for _ in range(2)]
        types = [e["type"] for e in events]
        assert "stream" in types
        assert "done" in types

        # Validate message contents
        stream_event = next(e for e in events if e["type"] == "stream")
        assert stream_event["payload"]["delta"] == "Echo: hello"
        assert stream_event["session_id"] == "test-session"

        done_event = next(e for e in events if e["type"] == "done")
        assert "usage" in done_event["payload"]
        assert done_event["session_id"] == "test-session"
