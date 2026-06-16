"""Security tests for memory tenant isolation.

CRITICAL: These tests verify that user A's memories are NEVER visible to
user B, even when searching for semantically related terms.  This is the
tenant-isolation boundary described in ``.agents/skills/chromadb.md``.
"""

from __future__ import annotations

import pytest

from app.memory.chroma import add_memory, search_memories


@pytest.mark.asyncio
async def test_no_cross_user_leakage() -> None:
    """User A's secret content must NEVER appear in user B's search results."""
    await add_memory(
        "user-A", "session-1", "user",
        "My secret project is called Phoenix",
    )
    await add_memory(
        "user-B", "session-2", "user",
        "I like hiking on weekends",
    )

    # User B searches for user A's secret — must get nothing about Phoenix
    results_for_b = await search_memories("user-B", "what is my secret project?")
    assert not any("Phoenix" in r for r in results_for_b), (
        f"Cross-user leakage detected! User B saw: {results_for_b}"
    )

    # User A should still see their own data
    results_for_a = await search_memories("user-A", "what is my secret project?")
    assert any("Phoenix" in r for r in results_for_a)


@pytest.mark.asyncio
async def test_search_filters_by_user_id_exactly() -> None:
    """Three users store data; each must only see their own memories."""
    await add_memory("alice", "s1", "user", "I love Python programming")
    await add_memory("bob", "s2", "user", "I love Rust programming")
    await add_memory("carol", "s3", "user", "I love Go programming")

    results_alice = await search_memories("alice", "what programming language?")
    results_bob = await search_memories("bob", "what programming language?")
    results_carol = await search_memories("carol", "what programming language?")

    # Each user should ONLY see their own language
    assert any("Python" in r for r in results_alice)
    assert not any("Rust" in r or "Go" in r for r in results_alice), (
        f"Alice saw other users' data: {results_alice}"
    )

    assert any("Rust" in r for r in results_bob)
    assert not any("Python" in r or "Go" in r for r in results_bob), (
        f"Bob saw other users' data: {results_bob}"
    )

    assert any("Go" in r for r in results_carol)
    assert not any("Python" in r or "Rust" in r for r in results_carol), (
        f"Carol saw other users' data: {results_carol}"
    )
