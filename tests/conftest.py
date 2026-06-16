"""Shared test fixtures for the Archimedes test suite."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

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


# Intentionally global (autouse=True, not scoped to memory tests only).
# Overhead is negligible (tmp_path + one monkeypatch + two global resets)
# and this guarantees isolation for ANY future test that touches memory
# indirectly, without needing per-directory conftest upkeep.
@pytest.fixture(autouse=True)
def _isolate_chroma(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Reset ChromaDB singletons and redirect storage to a temp dir per test.

    This prevents cross-test memory leakage and keeps the working directory
    clean of test artifacts.
    """
    import app.memory.chroma as chroma_mod

    chroma_mod._client = None
    chroma_mod._collection = None

    from app.core.config import get_settings
    monkeypatch.setattr(get_settings(), "chroma_path", str(tmp_path / "chroma"))

    yield

    chroma_mod._client = None
    chroma_mod._collection = None
