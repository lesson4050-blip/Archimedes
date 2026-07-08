"""Unit tests for the WorkerAgent class."""

from __future__ import annotations
from collections.abc import AsyncIterator
from unittest.mock import MagicMock, patch
import pytest
from app.agents.worker import WorkerAgent, WORKER_SYSTEM_PROMPT
from app.memory.blackboard import SharedBlackboard, BlackboardEntry
from app.models.base import ModelAdapter


@pytest.mark.asyncio
@patch("app.agents.worker._run_with_semaphore")
async def test_worker_executes_via_semaphore_not_directly(mock_run_sem: MagicMock) -> None:
    """Verify that WorkerAgent calls _run_with_semaphore instead of adapter.stream directly."""
    mock_run_sem.return_value = "worker output"
    blackboard = SharedBlackboard()
    adapter = MagicMock(spec=ModelAdapter)

    worker = WorkerAgent(
        worker_id="test-worker",
        step_index=2,
        step_description="Subtask C",
        adapter=adapter,
        blackboard=blackboard,
    )

    result = await worker.execute("Do complex task", dep_indices=set())

    assert result == "worker output"
    mock_run_sem.assert_called_once()
    # Confirm adapter.stream was never called directly
    adapter.stream.assert_not_called()


@pytest.mark.asyncio
async def test_worker_writes_result_to_blackboard() -> None:
    """Verify that the worker writes its execution result back to the blackboard."""
    class _DummyAdapter(ModelAdapter):
        async def stream(
            self,
            messages: list[dict[str, str]],
            *,
            max_tokens: int = 2048,
            temperature: float = 0.7,
            think: bool = False,
        ) -> AsyncIterator[str]:
            yield "success result"

    blackboard = SharedBlackboard()
    adapter = _DummyAdapter()
    worker = WorkerAgent(
        worker_id="test-worker",
        step_index=1,
        step_description="Subtask B",
        adapter=adapter,
        blackboard=blackboard,
    )

    await worker.execute("Do complex task", dep_indices=set())

    entry = await blackboard.read(1)
    assert entry is not None
    assert entry.step_index == 1
    assert entry.step_description == "Subtask B"
    assert entry.result == "success result"
    assert entry.worker_id == "test-worker"
    assert entry.completed_at != ""


@pytest.mark.asyncio
@patch("app.agents.worker._run_with_semaphore")
async def test_worker_includes_prerequisites_in_messages(mock_run_sem: MagicMock) -> None:
    """Verify that WorkerAgent includes prerequisite context in its user message."""
    mock_run_sem.return_value = "worker output"
    blackboard = SharedBlackboard()
    
    # Write a prereq to blackboard
    await blackboard.write(
        0,
        BlackboardEntry(
            step_index=0,
            step_description="Subtask A",
            result="Result A",
            worker_id="worker-a",
            completed_at="2026-07-08T23:55:00Z",
        ),
    )

    adapter = MagicMock(spec=ModelAdapter)
    worker = WorkerAgent(
        worker_id="test-worker",
        step_index=1,
        step_description="Subtask B",
        adapter=adapter,
        blackboard=blackboard,
    )

    await worker.execute("Do complex task", dep_indices={0})

    mock_run_sem.assert_called_once()
    called_messages = mock_run_sem.call_args[0][1]

    # Verify message structure
    assert len(called_messages) == 2
    assert called_messages[0] == {"role": "system", "content": WORKER_SYSTEM_PROMPT}
    
    user_content = called_messages[1]["content"]
    assert "Overall task: Do complex task" in user_content
    assert "Context from previous steps:" in user_content
    assert "Step 1 (Subtask A): Result A" in user_content
    assert "Your specific step: Subtask B" in user_content
