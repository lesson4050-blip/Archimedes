"""Unit tests for the SharedBlackboard and BlackboardEntry."""

from __future__ import annotations
import asyncio
import pytest
from app.memory.blackboard import SharedBlackboard, BlackboardEntry


@pytest.mark.asyncio
async def test_write_and_read_returns_entry() -> None:
    """Verify that writing an entry and reading it back returns correct data."""
    blackboard = SharedBlackboard()
    entry = BlackboardEntry(
        step_index=0,
        step_description="First step",
        result="Success",
        worker_id="worker-1",
        completed_at="2026-07-08T23:55:00Z",
    )
    await blackboard.write(0, entry)
    read_entry = await blackboard.read(0)
    assert read_entry == entry


@pytest.mark.asyncio
async def test_read_missing_returns_none() -> None:
    """Verify that reading a non-existent step returns None."""
    blackboard = SharedBlackboard()
    assert await blackboard.read(99) is None


@pytest.mark.asyncio
async def test_read_prerequisites_returns_sorted_results() -> None:
    """Verify that read_prerequisites returns formatted, sorted context strings."""
    blackboard = SharedBlackboard()
    entry1 = BlackboardEntry(
        step_index=0,
        step_description="Task A",
        result="Result A",
        worker_id="worker-a",
        completed_at="2026-07-08T23:55:00Z",
    )
    entry2 = BlackboardEntry(
        step_index=1,
        step_description="Task B",
        result="Result B",
        worker_id="worker-b",
        completed_at="2026-07-08T23:55:05Z",
    )
    await blackboard.write(0, entry1)
    await blackboard.write(1, entry2)

    prereqs = await blackboard.read_prerequisites({1, 0})
    assert len(prereqs) == 2
    assert prereqs[0] == "Step 1 (Task A): Result A"
    assert prereqs[1] == "Step 2 (Task B): Result B"


@pytest.mark.asyncio
async def test_concurrent_writes_are_safe() -> None:
    """Verify that writing to the blackboard concurrently does not cause race conditions."""
    blackboard = SharedBlackboard()

    async def write_step(idx: int) -> None:
        entry = BlackboardEntry(
            step_index=idx,
            step_description=f"Step {idx}",
            result=f"Result {idx}",
            worker_id=f"worker-{idx}",
            completed_at="2026-07-08T23:55:00Z",
        )
        await blackboard.write(idx, entry)

    # Launch concurrent writes
    await asyncio.gather(*[write_step(i) for i in range(50)])

    # Verify all were written successfully
    for i in range(50):
        entry = await blackboard.read(i)
        assert entry is not None
        assert entry.step_index == i
        assert entry.result == f"Result {i}"
