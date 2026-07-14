# tests/unit/test_mcts_planner.py
from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

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
        self.calls: list[dict[str, Any]] = []

    async def stream(
        self,
        messages: list[dict[str, str]],
        *,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        think: bool = False,
    ) -> AsyncIterator[str]:
        self.call_count += 1
        self.calls.append({
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "think": think,
        })
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


@pytest.mark.anyio
async def test_mcts_passes_think_false_to_all_stream_calls() -> None:
    """Verify that both _expand and _simulate stream calls pass think=False."""
    # We do 1 iteration of search, which will trigger 1 _expand and 1 _simulate call.
    adapter = _ScriptedAdapter([])
    planner = MCTSPlanner(adapter, max_iterations=1)
    await planner.search("test task")

    assert len(adapter.calls) >= 2
    # Check that both calls had think=False passed
    for call in adapter.calls:
        assert call["think"] is False


@pytest.mark.anyio
async def test_expand_includes_tool_descriptions_when_tools_registered() -> None:
    """Test that MCTSPlanner._expand includes registered tool descriptions in the prompt."""
    from app.tools.registry import tool_registry
    from app.tools.base import BaseTool, ToolResult

    class FakeSearchTool(BaseTool):
        name: str = "fake_search"
        description: str = "Use this to search fake stuff."
        parameters_schema: dict[str, str] = {"query": "the search query"}

        async def execute(self, *, query: str = "", **kwargs: str) -> ToolResult:
            return ToolResult(tool_name=self.name, success=True, output="fake output")

    original_tools = dict(tool_registry._tools)
    try:
        tool_registry.register(FakeSearchTool())

        adapter = _ScriptedAdapter([])
        planner = MCTSPlanner(adapter)
        node = PlanNode(action=None, parent=None, depth=0)
        
        await planner._expand(node, "find latest news")

        # Assert that there was at least one call to the LLM
        assert len(adapter.calls) > 0
        # Assert that the prompt passed to the adapter contained the tool name and description
        last_call_messages = adapter.calls[-1]["messages"]
        user_message_content = next(
            msg["content"] for msg in last_call_messages if msg["role"] == "user"
        )
        assert "fake_search" in user_message_content
        assert "Use this to search fake stuff" in user_message_content
    finally:
        tool_registry._tools = original_tools


@pytest.mark.anyio
async def test_expand_deduplicates_identical_steps() -> None:
    """Test that _expand removes duplicate steps produced by the LLM."""
    # The LLM returns three steps but the first two are identical.
    expand_response = (
        "STEP: use web_search to find latest news | TERMINAL: NO\n"
        "STEP: use web_search to find latest news | TERMINAL: NO\n"
        "STEP: summarize findings for the user | TERMINAL: YES"
    )
    adapter = _ScriptedAdapter([expand_response, "0.5"])
    planner = MCTSPlanner(adapter, max_iterations=1)
    root = PlanNode(action=None, parent=None, depth=0)
    children = await planner._expand(root, "find latest news")

    # Only 2 unique children should remain (duplicate removed)
    assert len(children) == 2
    actions = [c.action for c in children]
    assert actions[0] == "use web_search to find latest news"
    assert actions[1] == "summarize findings for the user"
