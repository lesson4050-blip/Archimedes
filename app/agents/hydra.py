"""HydraSwarm coordinator, GPU serialization, and dependency resolution."""

from __future__ import annotations
import asyncio
from collections import defaultdict, deque
import re
from typing import TYPE_CHECKING
import uuid

if TYPE_CHECKING:
    from app.core.ws_hub import WSHub
    from app.models.base import ModelAdapter

from app.memory.blackboard import SharedBlackboard


# Module-level semaphore — one inference at a time across ALL workers
_GPU_SEMAPHORE = asyncio.Semaphore(1)


async def _run_with_semaphore(
    adapter: ModelAdapter,
    messages: list[dict[str, str]],
) -> str:
    """Acquire GPU slot before inference, release after. Never skip this.

    Args:
        adapter: The model adapter to stream from.
        messages: The message history list to pass to the model.

    Returns:
        The concatenated generated response string.
    """
    async with _GPU_SEMAPHORE:
        chunks: list[str] = []
        async for delta in adapter.stream(messages, think=False):
            chunks.append(delta)
        return "".join(chunks)


class DependencyGraph:
    """Topological sort of plan steps based on inter-step dependencies."""

    def __init__(self, steps: list[str]) -> None:
        """Initialize DependencyGraph.

        Args:
            steps: The list of step descriptions in the plan.
        """
        self.steps = steps
        self.deps: dict[int, set[int]] = defaultdict(set)

    def add_dependency(self, dependent: int, dependency: int) -> None:
        """Step `dependent` cannot start until step `dependency` completes.

        Args:
            dependent: The index of the dependent step.
            dependency: The index of the step it depends on.
        """
        self.deps[dependent].add(dependency)

    def topological_batches(self) -> list[list[int]]:
        """Return steps grouped into parallel batches.

        Steps in the same batch have no interdependencies and can run
        concurrently. Batches must be executed sequentially.

        Returns:
            A list of batches, where each batch is a list of step indices.

        Raises:
            ValueError: If a dependency cycle is detected.
        """
        in_degree = {i: len(self.deps[i]) for i in range(len(self.steps))}
        queue = deque(i for i in range(len(self.steps)) if in_degree[i] == 0)
        batches: list[list[int]] = []

        while queue:
            batch = list(queue)
            queue.clear()
            # Sort the batch to ensure deterministic ordering
            batch.sort()
            batches.append(batch)
            for idx in batch:
                for j in range(len(self.steps)):
                    if idx in self.deps[j]:
                        in_degree[j] -= 1
                        if in_degree[j] == 0:
                            queue.append(j)

        # Validate that all nodes were processed (cycle detection)
        total_nodes_in_batches = sum(len(b) for b in batches)
        if total_nodes_in_batches != len(self.steps):
            raise ValueError("Dependency cycle detected")

        return batches


class HydraCoordinator:
    """Orchestrates parallel execution of a plan via WorkerAgents."""

    MAX_WORKERS = 5

    async def run(
        self,
        plan: list[str],
        original_task: str,
        adapter: ModelAdapter,
        hub: WSHub,
        session_id: str,
    ) -> str:
        """Execute plan steps concurrently in topological batches.

        Args:
            plan: List of step descriptions.
            original_task: The overall task query.
            adapter: ModelAdapter for LLM calls.
            hub: WebSocket hub for broadcasting events.
            session_id: Active session ID.

        Returns:
            The aggregated results from all successful worker runs.
        """
        if not plan:
            return ""

        # Enforce MAX_WORKERS — truncate if plan is huge
        plan = plan[: self.MAX_WORKERS]

        blackboard = SharedBlackboard()
        graph = await self._build_dependency_graph(plan, adapter)
        batches = graph.topological_batches()

        # Broadcast swarm_start event
        await hub.send_swarm_start(session_id, len(plan), batches)

        from app.agents.worker import WorkerAgent

        for batch_idx, batch in enumerate(batches):
            await hub.send_stream(
                session_id,
                f"\n🐙 Batch {batch_idx + 1}/{len(batches)}: "
                f"running {len(batch)} agent(s) in parallel...\n",
            )

            workers = [
                WorkerAgent(
                    worker_id=f"worker-{uuid.uuid4().hex[:6]}",
                    step_index=i,
                    step_description=plan[i],
                    adapter=adapter,
                    blackboard=blackboard,
                )
                for i in batch
            ]

            # Broadcast worker_start events
            for w in workers:
                await hub.send_worker_start(session_id, w.step_index, w.step_description)

            # Execute batch tasks concurrently
            results = await asyncio.gather(
                *[w.execute(original_task, graph.deps[w.step_index]) for w in workers],
                return_exceptions=True,
            )

            for worker, result in zip(workers, results):
                if isinstance(result, BaseException):
                    await hub.send_stream(
                        session_id,
                        f"⚠️ Worker {worker.worker_id} failed: {type(result).__name__}: {result}\n",
                    )
                else:
                    await hub.send_stream(
                        session_id,
                        f"✅ Step {worker.step_index + 1} complete\n",
                    )
                    preview = result[:100] + "..." if len(result) > 100 else result
                    await hub.send_worker_done(session_id, worker.step_index, preview)

        # Build aggregated result from blackboard in order
        final_outputs: list[str] = []
        for i in range(len(plan)):
            entry = await blackboard.read(i)
            if entry:
                final_outputs.append(f"Step {i + 1}: {entry.result}")
        return "\n\n".join(final_outputs)

    async def _build_dependency_graph(
        self, plan: list[str], adapter: ModelAdapter
    ) -> DependencyGraph:
        """Analyze the plan and build a dependency graph using LLM assistance.

        Args:
            plan: The truncated plan list.
            adapter: The ModelAdapter to query.

        Returns:
            The DependencyGraph instance with any detected dependencies.
        """
        graph = DependencyGraph(plan)
        try:
            # Build prompt for dependency analysis
            plan_text = "\n".join(f"Step {i+1}: {step}" for i, step in enumerate(plan))
            prompt = (
                "Identify dependencies between these steps:\n"
                f"{plan_text}\n\n"
                "If a step requires the output or result of a previous step to proceed, "
                "write exactly: 'Step N depends on Step M' (where N and M are the step numbers).\n"
                "Write nothing else."
            )
            messages = [{"role": "user", "content": prompt}]
            
            # Run with semaphore to serialize GPU access
            response = await _run_with_semaphore(adapter, messages)

            # Parse "Step N depends on Step M" patterns
            matches = re.findall(
                r"step\s+(\d+)\s+depends\s+on\s+step\s+(\d+)", response, re.IGNORECASE
            )
            for dep_str, prereq_str in matches:
                dep = int(dep_str) - 1
                prereq = int(prereq_str) - 1
                if 0 <= dep < len(plan) and 0 <= prereq < len(plan):
                    graph.add_dependency(dep, prereq)

            # Validate that the graph is cycle-free
            graph.topological_batches()
        except Exception:
            # Fail-safe: reset dependencies to empty on cycle or error
            graph.deps.clear()

        return graph
