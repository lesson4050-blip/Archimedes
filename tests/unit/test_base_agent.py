"""Unit tests for the BaseAgent class."""

from __future__ import annotations

from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agents.base import BaseAgent
from app.core.session import Session
from app.core.ws_hub import WSHub
from app.models.base import ModelAdapter
import pytest_mock


class MockAdapter(ModelAdapter):
    """Simple mock adapter that streams predefined tokens."""

    def __init__(self, deltas: list[str]) -> None:
        self.deltas = deltas

    async def stream(
        self,
        messages: list[dict[str, str]],
        *,
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        for delta in self.deltas:
            yield delta


@pytest.mark.asyncio
async def test_agent_appends_user_message_to_history() -> None:
    """Verify that the user's message is correctly appended to the session history."""
    adapter = MockAdapter(["Hello", " world"])
    agent = BaseAgent(adapter)
    
    session = Session(id="test-session", user_id="user1")
    hub = AsyncMock(spec=WSHub)

    await agent.run(session, "hello agent", hub)
    
    # Session history should have user message first
    assert len(session.history) >= 1
    assert session.history[0] == {"role": "user", "content": "hello agent"}


@pytest.mark.asyncio
async def test_agent_appends_assistant_message_to_history() -> None:
    """Verify that the assistant's complete streamed response is appended to the session history."""
    adapter = MockAdapter(["Hello", " world"])
    agent = BaseAgent(adapter)
    
    session = Session(id="test-session", user_id="user1")
    hub = AsyncMock(spec=WSHub)

    await agent.run(session, "hello agent", hub)
    
    # Session history should end with assistant response
    assert len(session.history) == 2
    assert session.history[1] == {"role": "assistant", "content": "Hello world"}


@pytest.mark.asyncio
async def test_agent_streams_via_hub() -> None:
    """Verify that the agent calls hub.send_stream for each delta and then send_done."""
    adapter = MockAdapter(["token1", "token2"])
    agent = BaseAgent(adapter)
    
    session = Session(id="test-session", user_id="user1")
    hub = AsyncMock(spec=WSHub)

    await agent.run(session, "hello", hub)

    # Check that stream was called for each token
    assert hub.send_stream.call_count == 2
    hub.send_stream.assert_any_call("test-session", "token1")
    hub.send_stream.assert_any_call("test-session", "token2")
    
    # Check that done was called
    hub.send_done.assert_called_once_with("test-session", {"prompt_tokens": 0, "completion_tokens": 0})


@pytest.mark.asyncio
async def test_agent_stops_on_cancel() -> None:
    """Verify that the agent stops streaming if session.cancel_requested becomes True."""
    class CancellingAdapter(ModelAdapter):
        async def stream(
            self,
            messages: list[dict[str, str]],
            *,
            max_tokens: int = 2048,
            temperature: float = 0.7,
        ) -> AsyncIterator[str]:
            yield "first"
            # Set cancellation flag
            session.cancel_requested = True
            yield "second"

    adapter = CancellingAdapter()
    agent = BaseAgent(adapter)
    
    session = Session(id="test-session", user_id="user1")
    hub = AsyncMock(spec=WSHub)

    await agent.run(session, "hello", hub)

    # Should only have sent the first token
    assert hub.send_stream.call_count == 1
    hub.send_stream.assert_called_once_with("test-session", "first")
    
    # Session history assistant content should only contain the first token
    assert session.history[1] == {"role": "assistant", "content": "first"}


@pytest.mark.asyncio
async def test_agent_does_not_persist_assistant_memory_on_exception(
    mocker: pytest_mock.MockerFixture,
) -> None:
    """Verify that assistant memory is NOT persisted if an exception occurs mid-stream."""
    class FailingAdapter(ModelAdapter):
        async def stream(
            self,
            messages: list[dict[str, str]],
            *,
            max_tokens: int = 2048,
            temperature: float = 0.7,
        ) -> AsyncIterator[str]:
            yield "first"
            raise ValueError("Failing mid-stream")

    mock_add_memory = mocker.patch("app.agents.base.add_memory", new_callable=AsyncMock)
    adapter = FailingAdapter()
    agent = BaseAgent(adapter)

    session = Session(id="test-session", user_id="user1")
    hub = AsyncMock(spec=WSHub)

    await agent.run(session, "hello", hub)

    # Verify that add_memory was not called with role="assistant"
    for call in mock_add_memory.call_args_list:
        args, kwargs = call
        assert args[2] != "assistant"


@pytest.mark.asyncio
async def test_agent_does_not_persist_assistant_memory_on_cancel(
    mocker: pytest_mock.MockerFixture,
) -> None:
    """Verify that assistant memory is NOT persisted if the session is cancelled mid-stream."""
    class CancellingAdapter(ModelAdapter):
        async def stream(
            self,
            messages: list[dict[str, str]],
            *,
            max_tokens: int = 2048,
            temperature: float = 0.7,
        ) -> AsyncIterator[str]:
            yield "first"
            session.cancel_requested = True
            yield "second"

    mock_add_memory = mocker.patch("app.agents.base.add_memory", new_callable=AsyncMock)
    adapter = CancellingAdapter()
    agent = BaseAgent(adapter)

    session = Session(id="test-session", user_id="user1")
    hub = AsyncMock(spec=WSHub)

    await agent.run(session, "hello", hub)

    # Verify that add_memory was not called with role="assistant"
    for call in mock_add_memory.call_args_list:
        args, kwargs = call
        assert args[2] != "assistant"


@pytest.mark.asyncio
async def test_agent_still_persists_user_memory_even_on_failure(
    mocker: pytest_mock.MockerFixture,
) -> None:
    """Verify that user memory IS persisted even if generation fails mid-stream."""
    class FailingAdapter(ModelAdapter):
        async def stream(
            self,
            messages: list[dict[str, str]],
            *,
            max_tokens: int = 2048,
            temperature: float = 0.7,
        ) -> AsyncIterator[str]:
            yield "first"
            raise ValueError("Failing mid-stream")

    mock_add_memory = mocker.patch("app.agents.base.add_memory", new_callable=AsyncMock)
    adapter = FailingAdapter()
    agent = BaseAgent(adapter)

    session = Session(id="test-session", user_id="user1")
    hub = AsyncMock(spec=WSHub)

    await agent.run(session, "hello", hub)

    # Verify that add_memory was called for user message
    mock_add_memory.assert_any_call("user1", "test-session", "user", "hello")
