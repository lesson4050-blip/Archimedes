"""Integration test for cross-session memory recall.

Validates the Phase 2 done criteria from ``docs/ROADMAP.md``:
"Agent references information from a previous session without being told."

Flow:
    Session 1 (same user): user tells agent "My favorite programming language is Rust"
    Session 2 (different session_id, same user): user asks "what language do I like?"
    → The injected memory context must contain "Rust" BEFORE the agent streams
      its response — proving recall came from the memory engine, not current-
      session history.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from unittest.mock import AsyncMock

import pytest

from app.agents.base import BaseAgent, _MEMORY_PREFIX
from app.core.session import Session
from app.core.ws_hub import WSHub
from app.memory.chroma import add_memory, search_memories
from app.models.base import ModelAdapter


class EchoAdapter(ModelAdapter):
    """Adapter that echoes back a fixed response for deterministic testing."""

    def __init__(self, response: str = "Sure!") -> None:
        self._response = response

    async def stream(
        self,
        messages: list[dict[str, str]],
        *,
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        yield self._response


@pytest.mark.asyncio
async def test_cross_session_recall() -> None:
    """Same user, two sessions — session 2 recalls data from session 1.

    This proves cross-session recall works via the memory engine, not via
    in-session history (we use exclude_session_id to verify).
    """
    user_id = "test-user-cross-session"
    session_1_id = "session-alpha"
    session_2_id = "session-beta"

    # ── Session 1: store a fact ─────────────────────────────────────
    session_1 = Session(id=session_1_id, user_id=user_id)
    hub = AsyncMock(spec=WSHub)
    agent = BaseAgent(EchoAdapter("Great choice!"))

    await agent.run(session_1, "My favorite programming language is Rust", hub)

    # Verify the memory was persisted (direct engine check)
    stored = await search_memories(user_id, "Rust", n_results=5)
    assert any("Rust" in s for s in stored), (
        f"Memory not stored from session 1: {stored}"
    )

    # ── Session 2: ask a related question ───────────────────────────
    session_2 = Session(id=session_2_id, user_id=user_id)
    hub_2 = AsyncMock(spec=WSHub)
    agent_2 = BaseAgent(EchoAdapter("You love Rust!"))

    await agent_2.run(session_2, "what language do I like?", hub_2)

    # The memory context system message should have been injected
    system_messages = [
        m for m in session_2.history
        if m.get("role") == "system"
        and m.get("content", "").startswith(_MEMORY_PREFIX)
    ]
    assert len(system_messages) == 1, (
        f"Expected exactly 1 memory-context system message, got {len(system_messages)}"
    )
    context_content = system_messages[0]["content"]
    assert "Rust" in context_content, (
        f"Memory context did not contain 'Rust': {context_content}"
    )

    # ── Prove it's truly cross-session, not same-session echo ───────
    cross_session_results = await search_memories(
        user_id,
        "what language do I like?",
        n_results=5,
        exclude_session_id=session_2_id,
    )
    assert any("Rust" in r for r in cross_session_results), (
        f"Cross-session recall failed after excluding session 2: {cross_session_results}"
    )
