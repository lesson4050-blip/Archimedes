"""Unit tests for long-term memory management and REST auth dependency."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone, timedelta
import pytest
from fastapi import HTTPException
from jose import jwt

from app.core.auth import get_current_user_id, create_access_token
from app.core.config import get_settings
from app.memory.chroma import add_memory, list_memories, delete_memory


def craft_token_no_sub() -> str:
    """Helper to craft a token without a sub claim."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    expire = now + timedelta(hours=settings.jwt_expiry_hours)
    to_encode = {
        "exp": expire,
    }
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


@pytest.mark.asyncio
async def test_list_memories_returns_only_owners_entries() -> None:
    """list_memories must return only the requesting user's entries, sorted chronologically descending."""
    user_a = "user-alice"
    user_b = "user-bob"

    # Store memories for user A and B
    await add_memory(user_a, "session-1", "user", "Alice first memory")
    await asyncio.sleep(0.01)
    await add_memory(user_a, "session-1", "assistant", "Alice second memory")
    await add_memory(user_b, "session-2", "user", "Bob first memory")

    # Fetch Alice's memories
    alice_memories = await list_memories(user_a)
    assert len(alice_memories) == 2

    # Verify keys and shape
    for entry in alice_memories:
        assert set(entry.keys()) == {"id", "content", "role", "session_id", "timestamp"}
        assert entry["session_id"] == "session-1"

    # Verify sort order: Alice's second memory (most recent) should be first
    assert alice_memories[0]["content"] == "Alice second memory"
    assert alice_memories[0]["role"] == "assistant"
    assert alice_memories[1]["content"] == "Alice first memory"
    assert alice_memories[1]["role"] == "user"

    # Fetch Bob's memories
    bob_memories = await list_memories(user_b)
    assert len(bob_memories) == 1
    assert bob_memories[0]["content"] == "Bob first memory"
    assert bob_memories[0]["role"] == "user"


@pytest.mark.asyncio
async def test_delete_memory_succeeds_for_owner() -> None:
    """Owner must be able to delete their own memory successfully."""
    user = "user-alice"
    await add_memory(user, "session-1", "user", "Alice memory")
    memories = await list_memories(user)
    assert len(memories) == 1
    memory_id = memories[0]["id"]

    # Delete memory
    deleted = await delete_memory(user, memory_id)
    assert deleted is True

    # Verify no longer exists
    memories_after = await list_memories(user)
    assert len(memories_after) == 0


@pytest.mark.asyncio
async def test_delete_memory_refuses_for_non_owner() -> None:
    """Non-owners must not be able to delete someone else's memory."""
    user_a = "user-alice"
    user_b = "user-bob"

    await add_memory(user_a, "session-1", "user", "Alice secret memory")
    memories_a = await list_memories(user_a)
    assert len(memories_a) == 1
    memory_id = memories_a[0]["id"]

    # Bob tries to delete Alice's memory — must fail (return False)
    deleted = await delete_memory(user_b, memory_id)
    assert deleted is False

    # Alice's memory must still exist
    memories_a_after = await list_memories(user_a)
    assert len(memories_a_after) == 1
    assert memories_a_after[0]["content"] == "Alice secret memory"


@pytest.mark.asyncio
async def test_get_current_user_id_rejects_missing_header() -> None:
    """get_current_user_id must raise 401 if header is missing or None."""
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user_id(None)
    assert exc_info.value.status_code == 401
    assert "Missing or invalid" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_current_user_id_rejects_malformed_header() -> None:
    """get_current_user_id must raise 401 if header is malformed."""
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user_id("Bearer")
    assert exc_info.value.status_code == 401

    with pytest.raises(HTTPException) as exc_info2:
        await get_current_user_id("Basic token123")
    assert exc_info2.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_id_accepts_valid_bearer_token() -> None:
    """get_current_user_id must return the user_id for a valid Bearer token."""
    token = create_access_token("valid-user")
    user_id = await get_current_user_id(f"Bearer {token}")
    assert user_id == "valid-user"


@pytest.mark.asyncio
async def test_get_current_user_id_rejects_token_with_empty_sub() -> None:
    """get_current_user_id must reject a token with an empty sub or missing sub claim."""
    # Empty sub
    token_empty = create_access_token("")
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user_id(f"Bearer {token_empty}")
    assert exc_info.value.status_code == 401

    # Missing sub
    token_missing = craft_token_no_sub()
    with pytest.raises(HTTPException) as exc_info2:
        await get_current_user_id(f"Bearer {token_missing}")
    assert exc_info2.value.status_code == 401
