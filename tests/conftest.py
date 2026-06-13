"""Shared test fixtures for the Archimedes test suite."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client() -> Iterator[TestClient]:
    """Provide a synchronous ``TestClient`` bound to the Archimedes app."""
    with TestClient(app) as c:
        yield c
