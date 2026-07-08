"""Specialist worker agent for executing isolated plan steps."""

from __future__ import annotations
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.base import ModelAdapter

from app.agents.hydra import _run_with_semaphore
from app.memory.blackboard import SharedBlackboard, BlackboardEntry


WORKER_SYSTEM_PROMPT = (
    "You are a specialist agent executing ONE specific task. "
    "Be direct. Output only what is requested for this specific step. "
    "Do not summarize other steps or add commentary."
)


class WorkerAgent:
    """Executes a single plan step, reads prerequisites from blackboard,
    writes result back to blackboard."""

    def __init__(
        self,
        worker_id: str,
        step_index: int,
        step_description: str,
        adapter: ModelAdapter,
        blackboard: SharedBlackboard,
    ) -> None:
        """Initialize the WorkerAgent.

        Args:
            worker_id: Unique string identifier for the worker.
            step_index: The 0-based step index in the plan.
            step_description: The description of this worker's task.
            adapter: ModelAdapter instance to use for inference.
            blackboard: SharedBlackboard instance to read and write.
        """
        self.worker_id = worker_id
        self.step_index = step_index
        self.step_description = step_description
        self.adapter = adapter
        self.blackboard = blackboard

    async def execute(
        self,
        original_task: str,
        dep_indices: set[int],
    ) -> str:
        """Execute this step and write result to blackboard.

        Args:
            original_task: The original user request.
            dep_indices: The set of step indices that this step depends on.

        Returns:
            The generated response string for this step.
        """
        prereqs = await self.blackboard.read_prerequisites(dep_indices)
        context = ""
        if prereqs:
            context = "Context from previous steps:\n" + "\n".join(prereqs) + "\n\n"

        messages = [
            {"role": "system", "content": WORKER_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Overall task: {original_task}\n\n"
                    f"{context}"
                    f"Your specific step: {self.step_description}"
                ),
            },
        ]

        result = await _run_with_semaphore(self.adapter, messages)

        await self.blackboard.write(
            self.step_index,
            BlackboardEntry(
                step_index=self.step_index,
                step_description=self.step_description,
                result=result,
                worker_id=self.worker_id,
                completed_at=datetime.now(timezone.utc).isoformat(),
            ),
        )
        return result
