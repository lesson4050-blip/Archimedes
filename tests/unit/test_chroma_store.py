"""Tests for the ChromaDB memory store (app/memory/chroma.py).

Uses a real temporary PersistentClient — not mocked — per the pattern
in ``.agents/skills/chromadb.md``.
"""

from __future__ import annotations

import pytest

from app.memory.chroma import add_memory, search_memories


@pytest.mark.asyncio
async def test_add_and_search_memory() -> None:
    """Store a memory and verify it can be retrieved via semantic search."""
    await add_memory("user-1", "session-a", "user", "My favorite color is teal")
    results = await search_memories("user-1", "what color do I like?")

    assert len(results) >= 1
    assert any("teal" in r for r in results)


@pytest.mark.asyncio
async def test_search_with_no_results_returns_empty_list() -> None:
    """Searching an empty collection must return an empty list, not raise."""
    results = await search_memories("user-nobody", "anything at all")
    assert results == []


@pytest.mark.asyncio
async def test_add_memory_skips_empty_content() -> None:
    """Adding empty or whitespace-only content should be a silent no-op."""
    # These should not raise or store anything
    await add_memory("user-1", "session-a", "user", "")
    await add_memory("user-1", "session-a", "user", "   ")
    await add_memory("user-1", "session-a", "user", "\n\t")

    # No memories should be stored
    results = await search_memories("user-1", "anything")
    assert results == []
