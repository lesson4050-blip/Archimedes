"""Integration tests for MCTS planner integration in session manager."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.agents.classifier import TaskComplexity
from app.agents.verify import VerificationResult
from app.models.ollama import OllamaAdapter


@patch("app.core.session.BaseAgent")
@patch("app.core.session.verify_plan_result")
@patch("app.core.session.MCTSPlanner")
@patch("app.core.session.classify_task")
def test_simple_message_bypasses_mcts(
    mock_classify: MagicMock,
    mock_mcts_class: MagicMock,
    mock_verify: MagicMock,
    mock_base_agent_class: MagicMock,
    client: TestClient,
    valid_token: str,
) -> None:
    """A simple message must bypass MCTS planning and run direct."""
    mock_classify.return_value = TaskComplexity.SIMPLE

    mock_agent_instance = mock_base_agent_class.return_value

    async def fake_run(session: Any, message: str, hub: Any) -> None:
        session.history.append({"role": "user", "content": message})
        await hub.send_stream(session.id, "direct response")
        session.history.append({"role": "assistant", "content": "direct response"})
        await hub.send_done(session.id, {"prompt_tokens": 0, "completion_tokens": 0})

    mock_agent_instance.run = AsyncMock(side_effect=fake_run)

    with client.websocket_connect(f"/ws/test-session?token={valid_token}") as ws:
        ws.send_json({
            "type": "task",
            "session_id": "test-session",
            "payload": {"message": "hello"},
        })

        # Expect exactly 2 events: stream, then done
        events = [ws.receive_json() for _ in range(2)]

        types = [e["type"] for e in events]
        assert "stream" in types
        assert "done" in types

        stream_event = next(e for e in events if e["type"] == "stream")
        assert stream_event["payload"]["delta"] == "direct response"

    mock_classify.assert_called_once()
    mock_mcts_class.assert_not_called()
    mock_verify.assert_not_called()


@patch("app.core.session.BaseAgent")
@patch("app.core.session.verify_plan_result")
@patch("app.core.session.MCTSPlanner")
@patch("app.core.session.classify_task")
def test_complex_message_triggers_mcts_path(
    mock_classify: MagicMock,
    mock_mcts_class: MagicMock,
    mock_verify: MagicMock,
    mock_base_agent_class: MagicMock,
    client: TestClient,
    valid_token: str,
) -> None:
    """A complex message must trigger MCTS planning and verification."""
    mock_classify.return_value = TaskComplexity.COMPLEX

    mock_planner_instance = mock_mcts_class.return_value
    mock_planner_instance.search = AsyncMock(
        return_value=["Step 1: do X", "Step 2: do Y"]
    )

    mock_verify.return_value = VerificationResult(passed=True, reason="")

    mock_agent_instance = mock_base_agent_class.return_value

    async def fake_run(session: Any, message: str, hub: Any) -> None:
        session.history.append({"role": "user", "content": message})
        await hub.send_stream(session.id, "agent response")
        session.history.append({"role": "assistant", "content": "agent response"})
        await hub.send_done(session.id, {"prompt_tokens": 0, "completion_tokens": 0})

    mock_agent_instance.run = AsyncMock(side_effect=fake_run)

    with client.websocket_connect(f"/ws/test-session?token={valid_token}") as ws:
        ws.send_json({
            "type": "task",
            "session_id": "test-session",
            "payload": {"message": "refactor code"},
        })

        # Expect exactly 5 events:
        # 1. planning
        # 2. "Complex task detected" stream
        # 3. "Plan:" stream
        # 4. "agent response" stream
        # 5. done
        events = [ws.receive_json() for _ in range(5)]

        types = [e["type"] for e in events]
        assert "planning" in types
        assert "stream" in types
        assert "done" in types

        planning_event = next(e for e in events if e["type"] == "planning")
        assert planning_event["payload"]["status"] == "planning"

        stream_deltas = [
            e["payload"]["delta"] for e in events if e["type"] == "stream"
        ]
        full_stream = "".join(stream_deltas)

        assert "Complex task detected" in full_stream
        assert "Plan:" in full_stream
        assert "1. Step 1: do X" in full_stream
        assert "2. Step 2: do Y" in full_stream
        assert "agent response" in full_stream

    mock_classify.assert_called_once()
    mock_mcts_class.assert_called_once()
    mock_planner_instance.search.assert_called_once_with("refactor code")
    mock_verify.assert_called_once()


@patch("app.core.session.BaseAgent")
@patch("app.core.session.verify_plan_result")
@patch("app.core.session.MCTSPlanner")
@patch("app.core.session.classify_task")
def test_complex_message_with_empty_plan_falls_back_to_direct(
    mock_classify: MagicMock,
    mock_mcts_class: MagicMock,
    mock_verify: MagicMock,
    mock_base_agent_class: MagicMock,
    client: TestClient,
    valid_token: str,
) -> None:
    """If MCTS search returns an empty plan, it must fall back to direct agent run."""
    mock_classify.return_value = TaskComplexity.COMPLEX

    mock_planner_instance = mock_mcts_class.return_value
    mock_planner_instance.search = AsyncMock(return_value=[])

    mock_agent_instance = mock_base_agent_class.return_value

    async def fake_run(session: Any, message: str, hub: Any) -> None:
        session.history.append({"role": "user", "content": message})
        await hub.send_stream(session.id, "direct fallback response")
        session.history.append(
            {"role": "assistant", "content": "direct fallback response"}
        )
        await hub.send_done(session.id, {"prompt_tokens": 0, "completion_tokens": 0})

    mock_agent_instance.run = AsyncMock(side_effect=fake_run)

    with client.websocket_connect(f"/ws/test-session?token={valid_token}") as ws:
        ws.send_json({
            "type": "task",
            "session_id": "test-session",
            "payload": {"message": "refactor code"},
        })

        # Expect exactly 5 events:
        # 1. planning
        # 2. "Complex task detected" stream
        # 3. "Could not build a plan" stream
        # 4. "direct fallback response" stream
        # 5. done
        events = [ws.receive_json() for _ in range(5)]

        types = [e["type"] for e in events]
        assert "planning" in types
        assert "stream" in types
        assert "done" in types

        stream_deltas = [
            e["payload"]["delta"] for e in events if e["type"] == "stream"
        ]
        full_stream = "".join(stream_deltas)

        assert "Could not build a plan" in full_stream
        assert "direct fallback response" in full_stream

    mock_classify.assert_called_once()
    mock_mcts_class.assert_called_once()
    mock_planner_instance.search.assert_called_once_with("refactor code")
    mock_verify.assert_not_called()

    # The agent run should be called with the original message
    mock_agent_instance.run.assert_called_once()
    assert mock_agent_instance.run.call_args[0][1] == "refactor code"


@patch("app.core.session.BaseAgent")
@patch("app.core.session.verify_plan_result")
@patch("app.core.session.MCTSPlanner")
@patch("app.core.session.classify_task")
def test_complex_message_with_failed_verification_shows_warning(
    mock_classify: MagicMock,
    mock_mcts_class: MagicMock,
    mock_verify: MagicMock,
    mock_base_agent_class: MagicMock,
    client: TestClient,
    valid_token: str,
) -> None:
    """If verification fails, a warning message must be appended to the stream."""
    mock_classify.return_value = TaskComplexity.COMPLEX

    mock_planner_instance = mock_mcts_class.return_value
    mock_planner_instance.search = AsyncMock(return_value=["Step 1"])

    mock_verify.return_value = VerificationResult(passed=False, reason="Incomplete")

    mock_agent_instance = mock_base_agent_class.return_value

    async def fake_run(session: Any, message: str, hub: Any) -> None:
        session.history.append({"role": "user", "content": message})
        await hub.send_stream(session.id, "bad response")
        session.history.append({"role": "assistant", "content": "bad response"})
        await hub.send_done(session.id, {"prompt_tokens": 0, "completion_tokens": 0})

    mock_agent_instance.run = AsyncMock(side_effect=fake_run)

    with client.websocket_connect(f"/ws/test-session?token={valid_token}") as ws:
        ws.send_json({
            "type": "task",
            "session_id": "test-session",
            "payload": {"message": "refactor code"},
        })

        # Expect exactly 6 events:
        # 1. planning
        # 2. "Complex task detected" stream
        # 3. "Plan:" stream
        # 4. "bad response" stream
        # 5. done
        # 6. "Verification note: Incomplete" stream
        events = [ws.receive_json() for _ in range(6)]

        types = [e["type"] for e in events]
        assert "planning" in types
        assert "stream" in types
        assert "done" in types

        stream_deltas = [
            e["payload"]["delta"] for e in events if e["type"] == "stream"
        ]
        full_stream = "".join(stream_deltas)

        assert "Verification note: Incomplete" in full_stream

    mock_classify.assert_called_once()
    mock_mcts_class.assert_called_once()
    mock_planner_instance.search.assert_called_once_with("refactor code")
    mock_verify.assert_called_once()
