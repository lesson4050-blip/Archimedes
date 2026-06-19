# tests/unit/test_mcts_planner.py
from __future__ import annotations

from collections.abc import AsyncIterator

import pytest

from app.agents.mcts import MCTSPlanner, PlanNode
from app.models.base import ModelAdapter


class _ScriptedAdapter(ModelAdapter):
    """Mock ModelAdapter that returns scripted responses and records calls.

    Generates fallback mock responses for expand and simulate if the pre-scripted
    list is depleted.
    """

    def __init__(self, responses: list[str]) -> None:
        self.responses = list(responses)
        self.call_count = 0

    async def stream(
        self,
        messages: list[dict[str, str]],
        *,
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        self.call_count += 1
        if self.responses:
            response = self.responses.pop(0)
        else:
            # _expand and _simulate use different max_tokens (500 vs 10) in mcts.py —
            # this is a more reliable discriminator than checking system prompt substrings.
            is_expand = max_tokens == 500
            if is_expand:
                response = "STEP: Default step | TERMINAL: NO"
            else:
                response = "0.5"
        yield response


@pytest.mark.anyio
async def test_search_respects_max_iterations() -> None:
    # We set max_iterations=5.
    # The absolute upper bound of LLM calls is max_iterations * 2, because
    # each iteration makes at most 1 expand and exactly 1 simulate call.
    max_iterations = 5
    adapter = _ScriptedAdapter([])
    planner = MCTSPlanner(adapter, max_iterations=max_iterations)
    await planner.search("test task")

    # Assert the precise bound: max_iterations * 2
    # The factor of 2 represents at-most-one-expand plus exactly-one-simulate per iteration.
    assert adapter.call_count <= max_iterations * 2
    assert adapter.call_count > 0


@pytest.mark.anyio
async def test_search_respects_max_depth() -> None:
    # Set max_depth=3. Even with infinite iterations, the resulting plan path
    # cannot exceed max_depth.
    max_depth = 3
    adapter = _ScriptedAdapter([])
    planner = MCTSPlanner(adapter, max_depth=max_depth, max_iterations=10)
    plan = await planner.search("test task")
    assert len(plan) <= max_depth


@pytest.mark.anyio
async def test_search_returns_empty_list_when_no_plan_found() -> None:
    # Scripted adapter returns empty response for expand, yielding no children.
    # root.children will remain empty, which causes the final plan extraction
    # to naturally return [] without triggering any while-loop.
    adapter = _ScriptedAdapter(["", "0.5", "", "0.5"])
    planner = MCTSPlanner(adapter, max_iterations=2)
    plan = await planner.search("test task")
    assert plan == []


def test_backpropagate_updates_all_ancestors_not_just_leaf() -> None:
    root = PlanNode(action=None, parent=None, depth=0)
    child = PlanNode(action="step1", parent=root, depth=1)
    grandchild = PlanNode(action="step2", parent=child, depth=2)
    
    root.children = [child]
    child.children = [grandchild]

    # Directly instantiate the planner with a dummy adapter
    dummy_adapter = _ScriptedAdapter([])
    planner = MCTSPlanner(dummy_adapter)
    planner._backpropagate(grandchild, 0.8)

    # Check grandchild
    assert grandchild.visit_count == 1
    assert grandchild.total_value == pytest.approx(0.8)

    # Check child
    assert child.visit_count == 1
    assert child.total_value == pytest.approx(0.8)

    # Check root
    assert root.visit_count == 1
    assert root.total_value == pytest.approx(0.8)


@pytest.mark.anyio
async def test_search_returns_nonempty_plan_with_terminal_node_scripted() -> None:
    # Suggest two steps, step 2 is terminal.
    # We pre-script the first expand response.
    # We pre-script the simulate responses as 0.9.
    expand_response = "STEP: Task step 1 | TERMINAL: NO\nSTEP: Task step 2 | TERMINAL: YES"
    adapter = _ScriptedAdapter([
        expand_response,  # First expand
        "0.9",            # First simulate
        "0.9",            # Subsequent simulations
    ])
    planner = MCTSPlanner(adapter, max_iterations=5)
    plan = await planner.search("do a thing")
    
    assert len(plan) > 0
    assert "Task step" in plan[0]
