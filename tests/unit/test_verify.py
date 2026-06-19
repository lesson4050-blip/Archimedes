# tests/unit/test_verify.py
from __future__ import annotations

from collections.abc import AsyncIterator

import pytest

from app.agents.verify import verify_plan_result, VerificationResult
from app.models.base import ModelAdapter


class _ScriptedAdapter(ModelAdapter):
    """Mock ModelAdapter that returns scripted responses and records calls."""

    def __init__(self, responses: list[str]) -> None:
        self.responses = list(responses)
        self.calls: list[dict[str, any]] = []

    async def stream(
        self,
        messages: list[dict[str, str]],
        *,
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        self.calls.append({
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
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
    ) -> AsyncIterator[str]:
        raise RuntimeError("Ollama connection failed")
        yield ""  # pragma: no cover


@pytest.mark.anyio
async def test_verify_returns_passed_true_on_yes_response() -> None:
    adapter = _ScriptedAdapter(["YES\nPlan solved the task successfully."])
    result = await verify_plan_result(adapter, "target task", "some result")
    assert result.passed is True
    assert result.reason == "Plan solved the task successfully."


@pytest.mark.anyio
async def test_verify_returns_passed_false_on_no_response() -> None:
    adapter = _ScriptedAdapter(["NO\nPlan missed the target constraints."])
    result = await verify_plan_result(adapter, "target task", "some result")
    assert result.passed is False
    assert result.reason == "Plan missed the target constraints."


@pytest.mark.anyio
async def test_verify_returns_passed_false_on_adapter_exception() -> None:
    adapter = _RaisingAdapter()
    result = await verify_plan_result(adapter, "target task", "some result")
    assert result.passed is False
    assert "Verification error" in result.reason


@pytest.mark.anyio
async def test_verify_extracts_reason_from_second_line() -> None:
    adapter = _ScriptedAdapter(["YES\nReason is on line 2\nAdditional info on line 3"])
    result = await verify_plan_result(adapter, "target task", "some result")
    assert result.passed is True
    assert result.reason == "Reason is on line 2\nAdditional info on line 3"
