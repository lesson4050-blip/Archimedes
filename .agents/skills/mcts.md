# Skill: MCTS Planner

## Trigger
Use when working on app/agents/classifier.py, app/agents/mcts.py,
app/agents/verify.py, or anything related to task complexity routing,
tree search planning, or self-verification of agent output.

---

## Why This Exists

Phase 1/2 gave us a single direct path: message -> stream -> response.
That's correct for "hello" but wrong for "refactor this module and add
tests and update the docs" — a task with multiple dependent steps where
a wrong first step wastes the whole attempt.

MCTS Planner adds a SECOND path for complex tasks: decompose into steps,
search over possible step sequences using UCB1, verify the result before
returning it. Simple tasks MUST still take the fast direct path — do not
route everything through MCTS, that would make "hi" take 10+ seconds again,
which is exactly the regression the May 2026 QA Runner audit fixed.

---

## Routing Decision: Classifier, Not Heuristics

We deliberately chose a real LLM call to classify task complexity instead
of keyword/length heuristics. This costs one extra Ollama round-trip per
message — keep that call as cheap as possible:

```python
# app/agents/classifier.py
from __future__ import annotations

from enum import Enum

from app.models.base import ModelAdapter


class TaskComplexity(str, Enum):
    SIMPLE = "SIMPLE"
    COMPLEX = "COMPLEX"


_CLASSIFIER_SYSTEM_PROMPT = (
    "You classify a user message as SIMPLE or COMPLEX.\n"
    "SIMPLE: greetings, single-fact questions, short requests answerable "
    "in one direct response.\n"
    "COMPLEX: multi-step tasks, requests requiring planning, tasks with "
    "multiple dependent actions (e.g. 'refactor X and add tests and update docs').\n"
    "Reply with EXACTLY ONE WORD: SIMPLE or COMPLEX. No punctuation, no explanation."
)


async def classify_task(adapter: ModelAdapter, message: str) -> TaskComplexity:
    """Classify a user message as SIMPLE or COMPLEX via a cheap LLM call.

    Fail-safe: any error, timeout, or unparseable response defaults to
    SIMPLE. We fail toward the FAST path, never toward the EXPENSIVE path —
    an unnecessary MCTS run is much costlier than an occasional under-planned
    simple response.
    """
    try:
        messages = [
            {"role": "system", "content": _CLASSIFIER_SYSTEM_PROMPT},
            {"role": "user", "content": message},
        ]
        chunks: list[str] = []
        async for delta in adapter.stream(messages, max_tokens=10, temperature=0.0):
            chunks.append(delta)
        raw = "".join(chunks).strip().upper()
        if "COMPLEX" in raw:
            return TaskComplexity.COMPLEX
        return TaskComplexity.SIMPLE
    except Exception:
        return TaskComplexity.SIMPLE
```

Keep `max_tokens=10` — we only need one word back. Keep `temperature=0.0` —
classification should be deterministic, not creative.

---

## MCTS Core: Node + UCB1

```python
# app/agents/mcts.py
from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass
class PlanNode:
    """One node in the search tree. action is the step taken to reach
    this node from its parent; None only for the root."""

    action: str | None
    parent: PlanNode | None
    depth: int
    children: list[PlanNode] = field(default_factory=list)
    visit_count: int = 0
    total_value: float = 0.0
    is_terminal: bool = False

    def ucb1_score(self, exploration_constant: float = 1.41421356) -> float:
        """Upper Confidence Bound. Unvisited nodes MUST be selected first —
        return infinity, not zero, or they'll never be explored."""
        if self.visit_count == 0:
            return float("inf")
        assert self.parent is not None
        exploitation = self.total_value / self.visit_count
        exploration = exploration_constant * math.sqrt(
            math.log(self.parent.visit_count) / self.visit_count
        )
        return exploitation + exploration

    def best_child(self) -> PlanNode:
        """Select child with highest UCB1 score. Caller must ensure children exist."""
        return max(self.children, key=lambda c: c.ucb1_score())

    def most_visited_child(self) -> PlanNode:
        """Final selection after search completes — use visit_count, not
        UCB1 score, since UCB1 is for exploration during search, not for
        the final answer. The most-visited path is the most-confirmed one."""
        return max(self.children, key=lambda c: c.visit_count)
```

---

## MCTS Search Loop — Hard Limits From Day One

```python
class MCTSPlanner:
    """Runs MCTS to decompose a complex task into a step plan.

    Hard limits are non-negotiable: without max_iterations and max_depth,
    a pathological task can spin the tree forever. This is the same class
    of bug as the April 2026 ExecutorAgent that returned after every tool
    call instead of only on results — uncapped loops are how agents hang.
    """

    def __init__(
        self,
        adapter: ModelAdapter,
        max_depth: int = 5,
        max_iterations: int = 20,
        exploration_constant: float = 1.41421356,
    ) -> None:
        self.adapter = adapter
        self.max_depth = max_depth
        self.max_iterations = max_iterations
        self.exploration_constant = exploration_constant

    async def search(self, task: str) -> list[str]:
        """Run MCTS and return the best plan as an ordered list of step
        descriptions. Returns an empty list if no viable plan was found
        within max_iterations — caller must handle this case explicitly,
        never assume a non-empty result."""
        root = PlanNode(action=None, parent=None, depth=0)

        for _ in range(self.max_iterations):
            node = self._select(root)
            if not node.is_terminal and node.depth < self.max_depth:
                children = await self._expand(node, task)
                node.children.extend(children)
                if children:
                    node = children[0]
            value = await self._simulate(node, task)
            self._backpropagate(node, value)

        return self._extract_best_plan(root)

    def _select(self, node: PlanNode) -> PlanNode:
        """Traverse via UCB1 until reaching a leaf (no children) or a
        terminal/max-depth node."""
        while node.children and not node.is_terminal and node.depth < self.max_depth:
            node = node.best_child()
        return node

    async def _expand(self, node: PlanNode, task: str) -> list[PlanNode]:
        """LLM call: given the task and the partial plan represented by
        the path from root to node, propose 2-3 candidate next steps.
        Mark a child terminal if its step text indicates task completion."""
        ...  # implementation calls self.adapter, parses N candidate steps

    async def _simulate(self, node: PlanNode, task: str) -> float:
        """Estimate how promising this path is, 0.0-1.0. Can be an LLM
        call asking 'how close does this plan get to solving the task',
        or for terminal nodes, defer to verify.py's verification result
        converted to a score."""
        ...

    def _backpropagate(self, node: PlanNode, value: float) -> None:
        """Walk up to root, incrementing visit_count and total_value on
        every ancestor — not just the leaf. This is the step most often
        forgotten; skipping it makes UCB1 scores at the root meaningless."""
        current: PlanNode | None = node
        while current is not None:
            current.visit_count += 1
            current.total_value += value
            current = current.parent

    def _extract_best_plan(self, root: PlanNode) -> list[str]:
        """Walk most_visited_child from root to a leaf, collecting actions."""
        plan: list[str] = []
        node = root
        while node.children:
            node = node.most_visited_child()
            if node.action:
                plan.append(node.action)
        return plan
```

---

## Self-Verification Gate — Mandatory, Not Optional

No MCTS-derived result reaches the user without passing through this gate.
A confidently-wrong multi-step result is worse than a slow correct one.

```python
# app/agents/verify.py
from __future__ import annotations

from dataclasses import dataclass

from app.models.base import ModelAdapter


@dataclass
class VerificationResult:
    passed: bool
    reason: str


_VERIFY_SYSTEM_PROMPT = (
    "You verify whether a result actually solves the stated task. "
    "Reply with YES or NO on the first line, then a one-sentence reason "
    "on the second line. Be strict — partial solutions are NO."
)


async def verify_plan_result(
    adapter: ModelAdapter, task: str, result: str
) -> VerificationResult:
    """Check whether `result` actually solves `task`. Fail-safe: any error
    or unparseable response is treated as a FAILED verification, not a
    passed one — we never let an error silently look like success."""
    try:
        messages = [
            {"role": "system", "content": _VERIFY_SYSTEM_PROMPT},
            {"role": "user", "content": f"Task: {task}\n\nResult: {result}"},
        ]
        chunks: list[str] = []
        async for delta in adapter.stream(messages, max_tokens=100, temperature=0.0):
            chunks.append(delta)
        raw = "".join(chunks).strip()
        lines = raw.split("\n", 1)
        passed = lines[0].strip().upper().startswith("YES")
        reason = lines[1].strip() if len(lines) > 1 else ""
        return VerificationResult(passed=passed, reason=reason)
    except Exception as e:
        return VerificationResult(passed=False, reason=f"Verification error: {e}")
```

Retry policy when verification fails: re-run search with the failure
reason appended to context, up to a small fixed retry cap (e.g. 2). After
the cap is exhausted, return an explicit failure — never silently return
the unverified result as if it passed.

---

## Testing Pattern — Mock ModelAdapter, Never Hit Real Ollama in Unit Tests

```python
# Reusable fake for MCTS unit tests
class _ScriptedAdapter(ModelAdapter):
    """Returns pre-scripted responses in order, one per call to stream()."""

    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)
        self.call_count = 0

    async def stream(self, messages, *, max_tokens=2048, temperature=0.7):
        self.call_count += 1
        response = self._responses.pop(0) if self._responses else ""
        yield response


# Test classifier fail-safe
async def test_classify_task_defaults_to_simple_on_error():
    class _RaisingAdapter(ModelAdapter):
        async def stream(self, *a, **kw):
            raise RuntimeError("boom")
            yield ""  # pragma: no cover — unreachable, satisfies generator typing

    result = await classify_task(_RaisingAdapter(), "anything")
    assert result == TaskComplexity.SIMPLE


# Test MCTS respects max_iterations as a hard cap
async def test_mcts_never_exceeds_max_iterations():
    adapter = _ScriptedAdapter([...])
    planner = MCTSPlanner(adapter, max_iterations=5)
    await planner.search("some complex task")
    # adapter.call_count must be bounded by a function of max_iterations,
    # not unbounded — assert the exact relationship your implementation
    # guarantees (e.g. <= max_iterations * calls_per_iteration)


# Test UCB1 math directly — no LLM involved at all
def test_unvisited_node_has_infinite_ucb1_score():
    parent = PlanNode(action=None, parent=None, depth=0, visit_count=10)
    child = PlanNode(action="step", parent=parent, depth=1, visit_count=0)
    assert child.ucb1_score() == float("inf")
```

---

## Common Pitfalls

- **Forgetting fail-safe direction**: classifier/verifier errors must fail
  toward SIMPLE/NOT-PASSED respectively — never toward the expensive or
  unverified path.
- **Backpropagating only the leaf**: UCB1 at the root is meaningless if
  ancestors never get their visit_count/total_value updated.
- **Returning UCB1-best instead of most-visited as the final plan**: UCB1
  balances explore/exploit DURING search; the final answer should be the
  path the search converged on (highest visit_count), not the path with
  the momentarily highest exploration bonus.
- **No max_depth check before expand**: always check `node.depth < max_depth`
  before expanding, or the tree grows past the intended bound by one level.
- **Treating an empty plan as success**: `search()` returning `[]` is a
  valid outcome (search exhausted iterations without finding a plan) —
  callers must check for this explicitly, not assume non-empty.
