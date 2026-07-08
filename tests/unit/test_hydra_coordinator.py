"""Unit tests for the HydraCoordinator and GPU semaphore integration."""

from __future__ import annotations
import asyncio
from collections.abc import AsyncIterator
from unittest.mock import AsyncMock

import pytest

from app.agents.hydra import HydraCoordinator, _run_with_semaphore
from app.agents.worker import WorkerAgent
from app.core.ws_hub import WSHub
from app.memory.blackboard import SharedBlackboard, BlackboardEntry
from app.models.base import ModelAdapter


@pytest.mark.asyncio
async def test_semaphore_serializes_concurrent_workers() -> None:
    """Even when workers run in parallel via asyncio.gather,
    actual LLM calls must be serialized by the semaphore.
    """
    call_times: list[float] = []

    class _TimingAdapter(ModelAdapter):
        async def stream(
            self,
            messages: list[dict[str, str]],
            *,
            max_tokens: int = 2048,
            temperature: float = 0.7,
            think: bool = False,
        ) -> AsyncIterator[str]:
            call_times.append(asyncio.get_running_loop().time())
            await asyncio.sleep(0.05)  # simulate inference time
            yield "result"

    adapter = _TimingAdapter()
    # Run 3 concurrent worker tasks
    await asyncio.gather(
        _run_with_semaphore(adapter, []),
        _run_with_semaphore(adapter, []),
        _run_with_semaphore(adapter, []),
    )

    assert len(call_times) == 3
    # Check that call times are spaced out by at least 0.045 seconds (no overlap)
    times = sorted(call_times)
    for i in range(len(times) - 1):
        assert times[i + 1] >= times[i] + 0.045


@pytest.mark.asyncio
async def test_coordinator_respects_max_workers_cap() -> None:
    """Verify that when a plan has more than 5 steps, coordinator truncates to 5 workers."""
    class _DummyAdapter(ModelAdapter):
        async def stream(
            self,
            messages: list[dict[str, str]],
            *,
            max_tokens: int = 2048,
            temperature: float = 0.7,
            think: bool = False,
        ) -> AsyncIterator[str]:
            yield "result"

    coordinator = HydraCoordinator()
    plan = [f"Step {i}" for i in range(10)]
    hub = AsyncMock(spec=WSHub)
    adapter = _DummyAdapter()

    res = await coordinator.run(plan, "Task", adapter, hub, "test-session")
    # It should truncate to 5 steps, and return Step 1 to Step 5
    assert "Step 1:" in res
    assert "Step 5:" in res
    assert "Step 6:" not in res


@pytest.mark.asyncio
async def test_coordinator_falls_back_on_empty_plan() -> None:
    """Verify run() with an empty plan returns empty string and doesn't crash."""
    coordinator = HydraCoordinator()
    hub = AsyncMock(spec=WSHub)
    adapter = AsyncMock(spec=ModelAdapter)
    res = await coordinator.run([], "Task", adapter, hub, "test-session")
    assert res == ""


@pytest.mark.asyncio
async def test_worker_receives_prerequisite_context_from_blackboard() -> None:
    """Verify B's execute receives A's result as context."""
    blackboard = SharedBlackboard()
    # Pre-fill step 0 on blackboard
    await blackboard.write(
        0,
        BlackboardEntry(
            step_index=0,
            step_description="First step",
            result="Prereq result",
            worker_id="worker-0",
            completed_at="2026-07-08T23:55:00Z",
        ),
    )

    captured_messages: list[dict[str, str]] = []

    class _CapturingAdapter(ModelAdapter):
        async def stream(
            self,
            messages: list[dict[str, str]],
            *,
            max_tokens: int = 2048,
            temperature: float = 0.7,
            think: bool = False,
        ) -> AsyncIterator[str]:
            nonlocal captured_messages
            captured_messages = messages
            yield "worker response"

    adapter = _CapturingAdapter()
    worker = WorkerAgent(
        worker_id="worker-1",
        step_index=1,
        step_description="Second step",
        adapter=adapter,
        blackboard=blackboard,
    )

    await worker.execute("Do the overall task", dep_indices={0})

    # Verify prereq context was injected in messages
    user_message = next(m["content"] for m in captured_messages if m["role"] == "user")
    assert "Context from previous steps:" in user_message
    assert "Step 1 (First step): Prereq result" in user_message
    assert "Second step" in user_message


@pytest.mark.asyncio
async def test_gather_returns_exceptions_not_raises() -> None:
    """Verify that if a worker raises an exception, the coordinator handles it and continues."""
    class _FailingAdapter(ModelAdapter):
        async def stream(
            self,
            messages: list[dict[str, str]],
            *,
            max_tokens: int = 2048,
            temperature: float = 0.7,
            think: bool = False,
        ) -> AsyncIterator[str]:
            user_msg = next(m["content"] for m in messages if m["role"] == "user")
            if "Failed step" in user_msg:
                raise ValueError("Worker execution failed")
            yield "success response"

    coordinator = HydraCoordinator()
    plan = ["Successful step", "Failed step"]
    hub = AsyncMock(spec=WSHub)
    adapter = _FailingAdapter()

    # Both steps are independent so they run in the same batch in parallel
    res = await coordinator.run(plan, "Task", adapter, hub, "test-session")

    # Hub should receive a stream warning
    stream_calls = [call.args[1] for call in hub.send_stream.call_args_list]
    assert any("failed" in call.lower() and "ValueError" in call for call in stream_calls)

    # Successful worker should have completed
    assert "Step 1: success response" in res
    assert "Step 2:" not in res  # Failed step not in results


@pytest.mark.asyncio
async def test_run_with_semaphore_passes_think_false() -> None:
    """Verify think=False is passed to the adapter during _run_with_semaphore execution."""
    captured_think = None

    class _DummyAdapter(ModelAdapter):
        async def stream(
            self,
            messages: list[dict[str, str]],
            *,
            max_tokens: int = 2048,
            temperature: float = 0.7,
            think: bool = False,
        ) -> AsyncIterator[str]:
            nonlocal captured_think
            captured_think = think
            yield "result"

    adapter = _DummyAdapter()
    await _run_with_semaphore(adapter, [])
    assert captured_think is False
