"""Integration tests for the WebSocket endpoint."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocketDisconnect


class _FakeAdapter:
    """A fake ModelAdapter that yields a single token without network calls."""

    async def stream(
        self,
        messages: list[dict[str, str]],
        *,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        think: bool = False,
    ) -> AsyncIterator[str]:
        """Yield a single test delta."""
        yield "mocked response"


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
    """Sending a task must stream a response and complete with done."""
    with patch("app.core.session.OllamaAdapter", return_value=_FakeAdapter()):
        with client.websocket_connect(f"/ws/test-session?token={valid_token}") as ws:
            ws.send_json({
                "type": "task",
                "session_id": "test-session",
                "payload": {"message": "hello"},
            })
            events: list[dict[str, Any]] = []
            for _ in range(2):
                events.append(ws.receive_json())

            types = [e["type"] for e in events]
            assert "stream" in types
            assert "done" in types

            stream_event = next(e for e in events if e["type"] == "stream")
            assert stream_event["payload"]["delta"] == "mocked response"
            assert stream_event["session_id"] == "test-session"

            done_event = next(e for e in events if e["type"] == "done")
            assert "usage" in done_event["payload"]
            assert done_event["session_id"] == "test-session"
