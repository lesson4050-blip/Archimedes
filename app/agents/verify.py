# app/agents/verify.py
from __future__ import annotations

from dataclasses import dataclass

from app.models.base import ModelAdapter


@dataclass
class VerificationResult:
    """The result of verifying if a plan solves a given task."""

    passed: bool
    reason: str


_VERIFY_SYSTEM_PROMPT = (
    "You verify whether a result actually solves the stated task. "
    "Reply with YES or NO on the first line, then a one-sentence reason "
    "on the second line. Be strict — partial solutions are NO."
)


async def verify_plan_result(
    adapter: ModelAdapter, task: str, result: str
) -> VerificationResult:
    """Check whether `result` actually solves `task`. Fail-safe: any error
    or unparseable response is treated as a FAILED verification, not a
    passed one — we never let an error silently look like success.
    """
    try:
        messages = [
            {"role": "system", "content": _VERIFY_SYSTEM_PROMPT},
            {"role": "user", "content": f"Task: {task}\n\nResult: {result}"},
        ]
        chunks: list[str] = []
        async for delta in adapter.stream(
            messages, max_tokens=100, temperature=0.0, think=False
        ):
            chunks.append(delta)
        raw = "".join(chunks).strip()
        lines = raw.split("\n", 1)
        passed = lines[0].strip().upper().startswith("YES")
        reason = lines[1].strip() if len(lines) > 1 else ""
        return VerificationResult(passed=passed, reason=reason)
    except Exception as e:
        return VerificationResult(passed=False, reason=f"Verification error: {e}")
