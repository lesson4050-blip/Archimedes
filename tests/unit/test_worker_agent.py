"""Unit tests for the WorkerAgent class."""

from __future__ import annotations
from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from app.agents.worker import (
    WorkerAgent,
    WORKER_SYSTEM_PROMPT,
    MAX_WORKER_TOOL_ITERATIONS,
)
from app.memory.blackboard import SharedBlackboard, BlackboardEntry
from app.models.base import ModelAdapter
from app.tools.base import BaseTool, ToolResult
from app.tools.registry import ToolRegistry


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

    # Verify message structure — system content includes WORKER_SYSTEM_PROMPT
    # (may be followed by tool descriptions and current date)
    assert len(called_messages) == 2
    assert called_messages[0]["role"] == "system"
    assert WORKER_SYSTEM_PROMPT in called_messages[0]["content"]

    user_content = called_messages[1]["content"]
    assert "Overall task: Do complex task" in user_content
    assert "Context from previous steps:" in user_content
    assert "Step 1 (Subtask A): Result A" in user_content
    assert "Your specific step: Subtask B" in user_content


# ── New tests ─────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
@patch("app.agents.worker.tool_registry")
@patch("app.agents.worker._run_with_semaphore")
async def test_worker_uses_tool_when_tool_call_detected(
    mock_run_sem: MagicMock,
    mock_registry: MagicMock,
) -> None:
    """Worker detects TOOL_CALL, executes tool, feeds result back, writes final answer."""
    # First LLM call: emit a tool call; second: emit the final answer
    mock_run_sem.side_effect = [
        "TOOL_CALL: fake_tool\nPARAMS: {\"query\": \"test\"}",
        "Final answer after tool",
    ]

    # Fake tool that succeeds
    class _FakeTool(BaseTool):
        name: str = "fake_tool"
        description: str = "A fake tool"
        parameters_schema: dict[str, str] = {"query": "The query"}

        async def execute(self, **kwargs: str) -> ToolResult:  # type: ignore[override]
            return ToolResult(tool_name="fake_tool", success=True, output="tool output")

    fake_registry = ToolRegistry()
    fake_registry.register(_FakeTool())

    mock_registry.all_tools.return_value = fake_registry.all_tools()
    mock_registry.tool_descriptions_for_prompt.return_value = (
        fake_registry.tool_descriptions_for_prompt()
    )
    mock_registry.execute = AsyncMock(
        return_value=ToolResult(tool_name="fake_tool", success=True, output="tool output")
    )

    blackboard = SharedBlackboard()
    adapter = MagicMock(spec=ModelAdapter)
    worker = WorkerAgent(
        worker_id="tool-worker",
        step_index=0,
        step_description="Search for something",
        adapter=adapter,
        blackboard=blackboard,
    )

    result = await worker.execute("Multi-step task", dep_indices=set())

    assert result == "Final answer after tool"
    assert mock_run_sem.call_count == 2
    mock_registry.execute.assert_called_once_with("fake_tool", {"query": "test"})

    entry = await blackboard.read(0)
    assert entry is not None
    assert entry.result == "Final answer after tool"


@pytest.mark.asyncio
@patch("app.agents.worker.tool_registry")
@patch("app.agents.worker._run_with_semaphore")
async def test_worker_respects_max_worker_tool_iterations(
    mock_run_sem: MagicMock,
    mock_registry: MagicMock,
) -> None:
    """Worker always emitting TOOL_CALL must exit loop after MAX_WORKER_TOOL_ITERATIONS calls."""

    class _FakeTool(BaseTool):
        name: str = "looping_tool"
        description: str = "Loops forever"
        parameters_schema: dict[str, str] = {}

        async def execute(self, **kwargs: str) -> ToolResult:  # type: ignore[override]
            return ToolResult(tool_name="looping_tool", success=True, output="looped")

    fake_registry = ToolRegistry()
    fake_registry.register(_FakeTool())

    mock_registry.all_tools.return_value = fake_registry.all_tools()
    mock_registry.tool_descriptions_for_prompt.return_value = (
        fake_registry.tool_descriptions_for_prompt()
    )
    mock_registry.execute = AsyncMock(
        return_value=ToolResult(tool_name="looping_tool", success=True, output="looped")
    )

    # Always return a TOOL_CALL so the loop never breaks early
    mock_run_sem.return_value = "TOOL_CALL: looping_tool\nPARAMS: {}"

    blackboard = SharedBlackboard()
    adapter = MagicMock(spec=ModelAdapter)
    worker = WorkerAgent(
        worker_id="loop-worker",
        step_index=0,
        step_description="Loop forever",
        adapter=adapter,
        blackboard=blackboard,
    )

    await worker.execute("Infinite loop task", dep_indices=set())

    # LLM must be called exactly MAX_WORKER_TOOL_ITERATIONS times — never more
    assert mock_run_sem.call_count == MAX_WORKER_TOOL_ITERATIONS


@pytest.mark.asyncio
@patch("app.agents.worker._run_with_semaphore")
async def test_worker_runs_directly_when_no_tool_call(mock_run_sem: MagicMock) -> None:
    """Worker with plain-text response makes exactly one LLM call and writes result."""
    mock_run_sem.return_value = "Direct answer, no tools needed"

    blackboard = SharedBlackboard()
    adapter = MagicMock(spec=ModelAdapter)
    worker = WorkerAgent(
        worker_id="direct-worker",
        step_index=0,
        step_description="Answer directly",
        adapter=adapter,
        blackboard=blackboard,
    )

    result = await worker.execute("Simple task", dep_indices=set())

    assert result == "Direct answer, no tools needed"
    mock_run_sem.assert_called_once()

    entry = await blackboard.read(0)
    assert entry is not None
    assert entry.result == "Direct answer, no tools needed"
