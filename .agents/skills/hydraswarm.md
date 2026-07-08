# Skill: HydraSwarm — Parallel Agent Orchestration

## Trigger
Use when working on app/agents/hydra.py, app/agents/worker.py,
app/memory/blackboard.py, or anything related to parallel agent
execution, dependency graphs, or multi-agent coordination.

---

## Core Concept

HydraSwarm runs multiple WorkerAgents in parallel for independent
subtasks. The key constraint: we have ONE GPU (RTX 3060 12GB) running
ONE model (qwen3:14b). Parallelism is in LOGIC and RESULT PROCESSING,
not in LLM inference. Workers share a single OllamaAdapter through an
asyncio.Semaphore queue — one inference at a time, multiple workers
waiting their turn.

```
HydraCoordinator
  ├── receives plan: list[str] from MCTSPlanner
  ├── builds DependencyGraph (topological sort)
  ├── launches WorkerAgents for independent steps
  │   ├── Worker 1: step A (no deps) → runs immediately
  │   ├── Worker 2: step B (no deps) → runs immediately
  │   └── Worker 3: step C (depends on A) → waits for A
  └── collects results via SharedBlackboard
```

---

## GPU Semaphore — CRITICAL

Without this, concurrent workers will deadlock or OOM the GPU.

```python
# app/agents/hydra.py
import asyncio

# Module-level semaphore — one inference at a time across ALL workers
_GPU_SEMAPHORE = asyncio.Semaphore(1)

async def _run_with_semaphore(adapter: ModelAdapter, messages: list[dict[str, str]]) -> str:
    """Acquire GPU slot before inference, release after. Never skip this."""
    async with _GPU_SEMAPHORE:
        chunks: list[str] = []
        async for delta in adapter.stream(messages, think=False):
            chunks.append(delta)
        return "".join(chunks)
```

Every worker MUST go through this. A worker that bypasses the semaphore
will cause all other workers to compete for GPU memory mid-inference,
producing garbage output or OOM errors.

---

## Dependency Graph

```python
# app/agents/hydra.py
from collections import defaultdict, deque

class DependencyGraph:
    """Topological sort of plan steps.

    Steps are independent by default. Dependencies are detected by
    asking the LLM classifier (cheap call, max_tokens=50) whether
    step B requires the output of step A. This is imperfect but
    good enough for Phase 4 — a step that wrongly runs in parallel
    will still produce output, just potentially lower quality.
    """

    def __init__(self, steps: list[str]) -> None:
        self.steps = steps
        self.deps: dict[int, set[int]] = defaultdict(set)
        # deps[i] = set of step indices that step i depends on

    def add_dependency(self, dependent: int, dependency: int) -> None:
        """Step `dependent` cannot start until step `dependency` completes."""
        self.deps[dependent].add(dependency)

    def topological_batches(self) -> list[list[int]]:
        """Return steps grouped into parallel batches.

        Steps in the same batch have no interdependencies and can run
        concurrently. Batches must be executed sequentially.

        Example:
            steps: [A, B, C, D]
            deps:  C depends on A, D depends on B
            result: [[A, B], [C, D]]
            → A and B run in parallel, then C and D run in parallel
        """
        in_degree = {i: len(self.deps[i]) for i in range(len(self.steps))}
        queue = deque(i for i in range(len(self.steps)) if in_degree[i] == 0)
        batches: list[list[int]] = []

        while queue:
            batch = list(queue)
            queue.clear()
            batches.append(batch)
            for idx in batch:
                for j in range(len(self.steps)):
                    if idx in self.deps[j]:
                        in_degree[j] -= 1
                        if in_degree[j] == 0:
                            queue.append(j)

        return batches
```

---

## SharedBlackboard

```python
# app/memory/blackboard.py
from __future__ import annotations
import asyncio
from dataclasses import dataclass, field


@dataclass
class BlackboardEntry:
    step_index: int
    step_description: str
    result: str
    worker_id: str
    completed_at: str  # ISO 8601


class SharedBlackboard:
    """Thread-safe shared memory for inter-agent communication.

    Workers write their results here. Dependent workers read from here
    to get context from prerequisite steps before starting their own work.

    Never share session.history between workers — each worker gets its
    own isolated history. The blackboard is the ONLY inter-worker
    communication channel.
    """

    def __init__(self) -> None:
        self._entries: dict[int, BlackboardEntry] = {}
        self._lock = asyncio.Lock()

    async def write(self, step_index: int, entry: BlackboardEntry) -> None:
        async with self._lock:
            self._entries[step_index] = entry

    async def read(self, step_index: int) -> BlackboardEntry | None:
        async with self._lock:
            return self._entries.get(step_index)

    async def read_prerequisites(self, dep_indices: set[int]) -> list[str]:
        """Return results of all prerequisite steps as context strings."""
        results: list[str] = []
        async with self._lock:
            for idx in sorted(dep_indices):
                entry = self._entries.get(idx)
                if entry:
                    results.append(
                        f"Step {idx + 1} ({entry.step_description}): {entry.result}"
                    )
        return results
```

---

## WorkerAgent

```python
# app/agents/worker.py
from __future__ import annotations

import uuid
from app.agents.hydra import _run_with_semaphore
from app.memory.blackboard import SharedBlackboard, BlackboardEntry
from app.models.base import ModelAdapter
from datetime import datetime, timezone

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
        """Execute this step and write result to blackboard."""
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
```

---

## HydraCoordinator

```python
# app/agents/hydra.py (continued)
class HydraCoordinator:
    """Orchestrates parallel execution of a plan via WorkerAgents.

    Flow:
    1. Receive plan steps from MCTSPlanner
    2. Build DependencyGraph (LLM-assisted dependency detection)
    3. Execute batches in topological order
    4. Stream progress to user via WSHub
    5. Return aggregated result
    """

    MAX_WORKERS = 5  # hard cap — prevent runaway spawning

    async def run(
        self,
        plan: list[str],
        original_task: str,
        adapter: ModelAdapter,
        hub: WSHub,
        session_id: str,
    ) -> str:
        if not plan:
            return ""

        # Enforce MAX_WORKERS — truncate if plan is huge
        plan = plan[: self.MAX_WORKERS]

        blackboard = SharedBlackboard()
        graph = await self._build_dependency_graph(plan, adapter)
        batches = graph.topological_batches()

        all_results: list[str] = []

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

            results = await asyncio.gather(
                *[w.execute(original_task, graph.deps[w.step_index]) for w in workers],
                return_exceptions=True,
            )

            for worker, result in zip(workers, results):
                if isinstance(result, Exception):
                    await hub.send_stream(
                        session_id,
                        f"⚠️ Worker {worker.worker_id} failed: {result}\n",
                    )
                else:
                    all_results.append(f"Step {worker.step_index + 1}: {result}")
                    await hub.send_stream(
                        session_id,
                        f"✅ Step {worker.step_index + 1} complete\n",
                    )

        return "\n\n".join(all_results)

    async def _build_dependency_graph(
        self, plan: list[str], adapter: ModelAdapter
    ) -> DependencyGraph:
        """Ask the LLM to identify dependencies between steps.
        Fail-safe: if LLM returns garbage, assume all steps are independent."""
        graph = DependencyGraph(plan)
        # Implementation: cheap LLM call, max_tokens=100, think=False
        # Parse response for "step N depends on step M" patterns
        # On any error: return graph with no dependencies (all parallel)
        return graph
```

---

## WebSocket Events for Swarm Progress

New event types to add to WSHub:
```python
# Send when swarm starts
{"type": "swarm_start", "payload": {"total_steps": N, "batches": K}}

# Send when a worker starts
{"type": "worker_start", "payload": {"step_index": i, "description": "..."}}

# Send when a worker completes
{"type": "worker_done", "payload": {"step_index": i, "result_preview": "..."}}
```

Frontend handles these to show per-step progress in the UI.

---

## Testing Pattern

```python
# NEVER use real OllamaAdapter in HydraSwarm tests
# Use _ScriptedAdapter pattern from mcts.md

# Critical test: semaphore prevents concurrent GPU access
async def test_semaphore_serializes_concurrent_workers():
    """Even when workers run in parallel via asyncio.gather,
    actual LLM calls must be serialized by the semaphore."""
    call_times: list[float] = []

    class _TimingAdapter(ModelAdapter):
        async def stream(self, messages, *, max_tokens=2048, temperature=0.7, think=False):
            call_times.append(asyncio.get_event_loop().time())
            await asyncio.sleep(0.05)  # simulate inference time
            yield "result"

    # Run 3 workers concurrently — calls must be sequential, not overlapping
    ...
    for i in range(len(call_times) - 1):
        assert call_times[i + 1] >= call_times[i] + 0.05  # no overlap

# Critical test: dependency graph produces correct batches
def test_topological_batches_with_diamond_dependency():
    """
    A → B → D
    A → C → D
    Expected batches: [[A], [B, C], [D]]
    """
    graph = DependencyGraph(["A", "B", "C", "D"])
    graph.add_dependency(1, 0)  # B depends on A
    graph.add_dependency(2, 0)  # C depends on A
    graph.add_dependency(3, 1)  # D depends on B
    graph.add_dependency(3, 2)  # D depends on C
    batches = graph.topological_batches()
    assert batches == [[0], [1, 2], [3]]
```

---

## Common Pitfalls

- **Bypassing the semaphore**: any worker that calls adapter.stream() directly
  (not through _run_with_semaphore) will race for GPU. Always go through it.
- **Sharing session.history between workers**: each worker must have its OWN
  isolated message history. The blackboard is the only shared state.
- **asyncio.gather swallowing exceptions**: always use return_exceptions=True,
  then check isinstance(result, Exception) per worker.
- **Infinite dependency cycles**: topological_batches() will loop forever on
  a cycle. Add a cycle detection check before running (if sum of batch sizes
  != len(steps), a cycle exists).
- **MAX_WORKERS without enforcement**: without the hard cap, a 20-step MCTS
  plan spawns 20 workers all waiting for the semaphore — memory leak.
