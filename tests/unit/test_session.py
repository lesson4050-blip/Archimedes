"""Unit tests for SessionManager and Session state."""

from __future__ import annotations

import pytest
from app.core.session import session_manager


@pytest.fixture(autouse=True)
def clean_sessions() -> None:
    """Clear sessions dictionary before each test to ensure isolation."""
    session_manager._sessions.clear()


def test_session_create_has_unique_id() -> None:
    """session_manager.create should produce sessions with unique UUIDs."""
    session1 = session_manager.create(user_id="user1")
    session2 = session_manager.create(user_id="user1")

    assert session1.id != session2.id
    assert len(session1.id) > 0
    assert session1.user_id == "user1"


def test_session_get_returns_none_for_unknown() -> None:
    """session_manager.get should return None if the session_id is not found."""
    assert session_manager.get("non-existent-session-id") is None


def test_session_get_or_create_idempotent() -> None:
    """session_manager.get_or_create should return the same session when called twice with same id."""
    session_id = "test-session-id"
    session1 = session_manager.get_or_create(session_id, user_id="user1")
    session2 = session_manager.get_or_create(session_id, user_id="user1")

    assert session1.id == session_id
    assert session2.id == session_id
    assert session1 is session2


@pytest.mark.asyncio
async def test_session_cancel_sets_flag() -> None:
    """session_manager.cancel should set cancel_requested flag to True."""
    session = session_manager.create(user_id="user1")
    assert session.cancel_requested is False

    await session_manager.cancel(session.id)
    assert session.cancel_requested is True
