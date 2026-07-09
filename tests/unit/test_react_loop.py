"""Unit tests for the agent's ReAct execution loop."""

from __future__ import annotations
from collections.abc import AsyncIterator, Generator
from unittest.mock import AsyncMock, patch
import pytest

from app.agents.base import BaseAgent
from app.core.session import Session
from app.core.ws_hub import WSHub
from app.tools.base import BaseTool, ToolResult
from app.tools.registry import ToolRegistry
from app.models.base import ModelAdapter


class ReActMockAdapter(ModelAdapter):
    """Mock model adapter returning sequential predefined responses for ReAct testing."""

    def __init__(self, responses: list[str]) -> None:
        self.responses = responses
        self.calls = 0
        self.messages_called: list[list[dict[str, str]]] = []

    async def stream(
        self,
        messages: list[dict[str, str]],
        *,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        think: bool = False,
    ) -> AsyncIterator[str]:
        self.messages_called.append(list(messages))
        idx = min(self.calls, len(self.responses) - 1)
        self.calls += 1
        yield self.responses[idx]


class FakeSearchTool(BaseTool):
    """Fake search tool to avoid real API calls during ReAct loop tests."""

    name: str = "web_search"
    description: str = "fake search"
    parameters_schema: dict[str, str] = {"query": "The query"}

    async def execute(self, *, query: str = "", **kwargs: str) -> ToolResult:
        return ToolResult(
            tool_name=self.name,
            success=True,
            output=f"Fake results for: {query}",
        )


@pytest.fixture
def clean_registry() -> Generator[ToolRegistry, None, None]:
    """Fixture replacing the global registry singleton with a clean one containing FakeSearchTool."""
    registry = ToolRegistry()
    registry.register(FakeSearchTool())
    with patch("app.tools.registry.tool_registry", new=registry):
        yield registry


@pytest.mark.asyncio
async def test_react_loop_executes_tool_and_injects_result(clean_registry: ToolRegistry) -> None:
    """Verify that a tool call triggers execution and injects result into the next prompt iteration."""
    responses = [
        'TOOL_CALL: web_search\nPARAMS: {"query": "today\'s news"}',
        'Here is the final answer based on the search results.'
    ]
    adapter = ReActMockAdapter(responses)
    agent = BaseAgent(adapter)
    session = Session(id="test-session", user_id="user1")
    hub = AsyncMock(spec=WSHub)
    
    await agent.run(session, "what's the news?", hub)
    
    assert adapter.calls == 2
    last_call_messages = adapter.messages_called[1]
    assert any("Fake results for: today's news" in m["content"] for m in last_call_messages)
    all_streamed = "".join(
        call[0][1] for call in hub.send_stream.call_args_list
    )
    assert "Here is the final answer" in all_streamed


@pytest.mark.asyncio
async def test_react_loop_terminates_after_max_iterations(clean_registry: ToolRegistry) -> None:
    """Verify that the ReAct loop breaks after 5 iterations to prevent infinite tool loops."""
    responses = ['TOOL_CALL: web_search\nPARAMS: {"query": "loop"}']
    adapter = ReActMockAdapter(responses)
    agent = BaseAgent(adapter)
    session = Session(id="test-session", user_id="user1")
    hub = AsyncMock(spec=WSHub)
    
    await agent.run(session, "run a loop", hub)
    
    assert adapter.calls == 5
    assert "I reached the maximum number of tool calls." in session.history[-1]["content"]


@pytest.mark.asyncio
async def test_react_loop_streams_tool_call_and_result_events(clean_registry: ToolRegistry) -> None:
    """Verify that tool call and result notifications are broadcasted as WebSocket events."""
    responses = [
        'TOOL_CALL: web_search\nPARAMS: {"query": "weather"}',
        'Final response'
    ]
    adapter = ReActMockAdapter(responses)
    agent = BaseAgent(adapter)
    session = Session(id="test-session", user_id="user1")
    hub = AsyncMock(spec=WSHub)
    
    await agent.run(session, "weather info", hub)
    
    broadcast_calls = hub.broadcast.call_args_list
    assert len(broadcast_calls) >= 2
    
    first_call_args = broadcast_calls[0][0][1]
    assert first_call_args["type"] == "tool_call"
    assert first_call_args["payload"]["tool"] == "web_search"
    assert first_call_args["payload"]["input"] == {"query": "weather"}
    
    second_call_args = broadcast_calls[1][0][1]
    assert second_call_args["type"] == "tool_result"
    assert second_call_args["payload"]["tool"] == "web_search"
    assert second_call_args["payload"]["success"] is True
    assert "Fake results for: weather" in second_call_args["payload"]["output"]


@pytest.mark.asyncio
async def test_react_loop_does_not_add_tool_messages_to_session_history(clean_registry: ToolRegistry) -> None:
    """Verify that tool message iterations do not pollute session.history."""
    responses = [
        'TOOL_CALL: web_search\nPARAMS: {"query": "history"}',
        'Final answer'
    ]
    adapter = ReActMockAdapter(responses)
    agent = BaseAgent(adapter)
    session = Session(id="test-session", user_id="user1")
    hub = AsyncMock(spec=WSHub)
    
    await agent.run(session, "hello", hub)
    
    assert len(session.history) == 2
    assert session.history[0] == {"role": "user", "content": "hello"}
    assert session.history[1] == {"role": "assistant", "content": "Final answer"}


@pytest.mark.asyncio
async def test_react_loop_respects_cancel_requested(clean_registry: ToolRegistry) -> None:
    """Verify that ReAct loop terminates immediately if a cancellation is requested."""
    class CancellingReActAdapter(ModelAdapter):
        def __init__(self) -> None:
            self.calls = 0
            
        async def stream(
            self,
            messages: list[dict[str, str]],
            *,
            max_tokens: int = 2048,
            temperature: float = 0.7,
            think: bool = False,
        ) -> AsyncIterator[str]:
            self.calls += 1
            yield 'TOOL_CALL: web_search\nPARAMS: {"query": "cancel"}'
            session.cancel_requested = True

    adapter = CancellingReActAdapter()
    agent = BaseAgent(adapter)
    session = Session(id="test-session", user_id="user1")
    hub = AsyncMock(spec=WSHub)
    
    await agent.run(session, "hello", hub)
    
    assert adapter.calls == 1
    assert not any(call[0][1] == "Final answer" for call in hub.send_stream.call_args_list)
