"""Shared test fixtures for the Archimedes test suite."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.core.auth import create_access_token
from app.main import app


@pytest.fixture()
def client() -> Iterator[TestClient]:
    """Provide a synchronous ``TestClient`` bound to the Archimedes app."""
    with TestClient(app) as c:
        yield c


@pytest.fixture
def valid_token() -> str:
    """Provide a valid JWT token fixture for testing."""
    return create_access_token(user_id="test-user")
