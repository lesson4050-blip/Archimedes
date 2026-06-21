# tests/unit/test_classifier.py
from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import pytest

from app.agents.classifier import classify_task, TaskComplexity
from app.models.base import ModelAdapter


class _ScriptedAdapter(ModelAdapter):
    """Mock ModelAdapter that returns scripted responses and records calls."""

    def __init__(self, responses: list[str]) -> None:
        self.responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    async def stream(
        self,
        messages: list[dict[str, str]],
        *,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        think: bool = False,
    ) -> AsyncIterator[str]:
        self.calls.append({
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "think": think,
        })
        response = self.responses.pop(0) if self.responses else ""
        yield response


class _RaisingAdapter(ModelAdapter):
    """Mock ModelAdapter that raises an exception during stream."""

    async def stream(
        self,
        messages: list[dict[str, str]],
        *,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        think: bool = False,
    ) -> AsyncIterator[str]:
        raise RuntimeError("Ollama connection failed")
        yield ""  # pragma: no cover


@pytest.mark.anyio
async def test_classify_task_returns_simple_for_greeting() -> None:
    adapter = _ScriptedAdapter(["SIMPLE"])
    result = await classify_task(adapter, "hello")
    assert result == TaskComplexity.SIMPLE


@pytest.mark.anyio
async def test_classify_task_returns_complex_for_multistep_request() -> None:
    adapter = _ScriptedAdapter(["COMPLEX"])
    result = await classify_task(adapter, "refactor code, run tests, and commit changes")
    assert result == TaskComplexity.COMPLEX


@pytest.mark.anyio
async def test_classify_task_defaults_to_simple_on_adapter_exception() -> None:
    adapter = _RaisingAdapter()
    result = await classify_task(adapter, "hello")
    assert result == TaskComplexity.SIMPLE


@pytest.mark.anyio
async def test_classify_task_defaults_to_simple_on_unparseable_response() -> None:
    adapter = _ScriptedAdapter(["unparseable garbage output"])
    result = await classify_task(adapter, "hello")
    assert result == TaskComplexity.SIMPLE


@pytest.mark.anyio
async def test_classify_task_uses_low_max_tokens() -> None:
    adapter = _ScriptedAdapter(["SIMPLE"])
    await classify_task(adapter, "hello")
    assert len(adapter.calls) == 1
    assert adapter.calls[0]["max_tokens"] == 10
    assert adapter.calls[0]["temperature"] == 0.0
    assert adapter.calls[0]["think"] is False
