"""Integration tests for long-term memory REST endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.auth import create_access_token
from app.memory.chroma import add_memory, list_memories


def test_get_memory_without_auth_returns_401(client: TestClient) -> None:
    """GET /memory without auth header must return 401."""
    response = client.get("/memory")
    assert response.status_code == 401
    assert "Missing or invalid" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_memory_with_valid_token_returns_200_with_correct_shape(client: TestClient) -> None:
    """GET /memory with valid JWT must return 200 and list of user's memories."""
    user_id = "test-user-api"
    await add_memory(user_id, "session-api", "user", "API integration test memory")

    token = create_access_token(user_id)
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/memory", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert "memories" in data
    memories = data["memories"]
    assert len(memories) == 1
    assert memories[0]["content"] == "API integration test memory"
    assert memories[0]["role"] == "user"
    assert memories[0]["session_id"] == "session-api"
    assert "id" in memories[0]
    assert "timestamp" in memories[0]


@pytest.mark.asyncio
async def test_delete_own_memory_returns_200(client: TestClient) -> None:
    """DELETE /memory/{id} for own memory must return 200 and delete status."""
    user_id = "test-user-api"
    await add_memory(user_id, "session-api", "user", "API memory to delete")

    # Retrieve ID
    memories = await list_memories(user_id)
    assert len(memories) == 1
    memory_id = memories[0]["id"]

    token = create_access_token(user_id)
    headers = {"Authorization": f"Bearer {token}"}
    response = client.delete(f"/memory/{memory_id}", headers=headers)

    assert response.status_code == 200
    assert response.json() == {"deleted": True}

    # Verify deleted
    memories_after = await list_memories(user_id)
    assert len(memories_after) == 0


@pytest.mark.asyncio
async def test_delete_others_memory_returns_404_not_403(client: TestClient) -> None:
    """DELETE /memory/{id} for another user's memory must return 404 to avoid leaking existence."""
    user_alice = "alice-user"
    user_bob = "bob-user"

    await add_memory(user_alice, "session-alice", "user", "Alice secret memory")
    memories = await list_memories(user_alice)
    assert len(memories) == 1
    memory_id = memories[0]["id"]

    # Bob tries to delete Alice's memory — must return 404
    token_bob = create_access_token(user_bob)
    headers = {"Authorization": f"Bearer {token_bob}"}
    response = client.delete(f"/memory/{memory_id}", headers=headers)

    assert response.status_code == 404
    assert response.json()["detail"] == "Memory not found"

    # Alice's memory must still exist
    memories_alice_after = await list_memories(user_alice)
    assert len(memories_alice_after) == 1
