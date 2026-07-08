"""Shared blackboard memory for multi-agent parallel execution coordination."""

from __future__ import annotations
import asyncio
from dataclasses import dataclass


@dataclass
class BlackboardEntry:
    """Represents a single completed step entry stored in the SharedBlackboard.

    Attributes:
        step_index: The 0-based index of the step in the plan.
        step_description: The description of the step.
        result: The result string produced by the worker.
        worker_id: The ID of the worker agent that executed this step.
        completed_at: ISO 8601 string timestamp when the step completed.
    """

    step_index: int
    step_description: str
    result: str
    worker_id: str
    completed_at: str


class SharedBlackboard:
    """Thread-safe shared memory for inter-agent communication.

    Workers write their results here. Dependent workers read from here
    to get context from prerequisite steps before starting their own work.
    """

    def __init__(self) -> None:
        """Initialize an empty SharedBlackboard with a synchronization lock."""
        self._entries: dict[int, BlackboardEntry] = {}
        self._lock: asyncio.Lock = asyncio.Lock()

    async def write(self, step_index: int, entry: BlackboardEntry) -> None:
        """Write a step result entry to the blackboard.

        Args:
            step_index: The 0-based index of the step.
            entry: The BlackboardEntry instance.
        """
        async with self._lock:
            self._entries[step_index] = entry

    async def read(self, step_index: int) -> BlackboardEntry | None:
        """Read a step entry from the blackboard by its index.

        Args:
            step_index: The 0-based index of the step.

        Returns:
            The BlackboardEntry if found, else None.
        """
        async with self._lock:
            return self._entries.get(step_index)

    async def read_prerequisites(self, dep_indices: set[int]) -> list[str]:
        """Return results of all prerequisite steps as formatted context strings.

        Args:
            dep_indices: A set of step indices representing prerequisites.

        Returns:
            A list of formatted strings describing each prerequisite step.
        """
        results: list[str] = []
        async with self._lock:
            for idx in sorted(dep_indices):
                entry = self._entries.get(idx)
                if entry:
                    results.append(
                        f"Step {idx + 1} ({entry.step_description}): {entry.result}"
                    )
        return results
