"""Unit tests for the Ollama model adapter."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.models.ollama import OllamaAdapter


async def _async_lines(lines: list[str]) -> AsyncIterator[str]:
    """Convert a list of strings into an async iterator."""
    for line in lines:
        yield line


class _FakeStreamResponse:
    """Fake httpx streaming response with async line iteration."""

    def __init__(self, lines: list[str]) -> None:
        self._lines = lines

    def raise_for_status(self) -> None:
        """No-op — fake response is always successful."""

    async def aiter_lines(self) -> AsyncIterator[str]:
        """Yield lines as an async iterator."""
        for line in self._lines:
            yield line

    async def aclose(self) -> None:
        """No-op close."""


class _FakeStreamCtx:
    """Fake context manager for httpx client.stream()."""

    def __init__(self, response: _FakeStreamResponse) -> None:
        self._response = response

    async def __aenter__(self) -> _FakeStreamResponse:
        return self._response

    async def __aexit__(self, *args: Any) -> None:
        pass


class _FakeClient:
    """Fake httpx.AsyncClient with stream() support."""

    def __init__(self, response: _FakeStreamResponse) -> None:
        self._response = response

    async def __aenter__(self) -> "_FakeClient":
        return self

    async def __aexit__(self, *args: Any) -> None:
        pass

    def stream(self, *args: Any, **kwargs: Any) -> _FakeStreamCtx:
        """Return a fake stream context manager."""
        return _FakeStreamCtx(self._response)


@pytest.mark.asyncio
async def test_ollama_adapter_streams_deltas() -> None:
    """Verify that the adapter yields text deltas correctly from NDJSON response."""
    lines = [
        '{"message": {"role": "assistant", "content": "Hello"}, "done": false}',
        '{"message": {"role": "assistant", "content": " world"}, "done": false}',
        '{"message": {"role": "assistant", "content": ""}, "done": true}',
    ]

    fake_response = _FakeStreamResponse(lines)
    fake_client = _FakeClient(fake_response)

    with patch("httpx.AsyncClient", return_value=fake_client):
        adapter = OllamaAdapter()
        deltas = [d async for d in adapter.stream([{"role": "user", "content": "hi"}])]

    assert deltas == ["Hello", " world"]


@pytest.mark.asyncio
async def test_ollama_adapter_raises_on_connection_error() -> None:
    """Verify that httpx.ConnectError raises RuntimeError with a helpful message."""
    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__ = AsyncMock(
            side_effect=httpx.ConnectError("Connection refused")
        )
        adapter = OllamaAdapter()
        with pytest.raises(RuntimeError, match="ollama serve"):
            async for _ in adapter.stream([{"role": "user", "content": "hi"}]):
                pass
