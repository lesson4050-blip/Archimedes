# app/agents/classifier.py
from __future__ import annotations

from enum import Enum

from app.models.base import ModelAdapter


class TaskComplexity(str, Enum):
    SIMPLE = "SIMPLE"
    COMPLEX = "COMPLEX"


_CLASSIFIER_SYSTEM_PROMPT = (
    "You classify a user message as SIMPLE or COMPLEX.\n"
    "SIMPLE: greetings, single-fact questions, short requests answerable "
    "in one direct response.\n"
    "COMPLEX: multi-step tasks, requests requiring planning, tasks with "
    "multiple dependent actions (e.g. 'refactor X and add tests and update docs').\n"
    "Reply with EXACTLY ONE WORD: SIMPLE or COMPLEX. No punctuation, no explanation."
)


async def classify_task(adapter: ModelAdapter, message: str) -> TaskComplexity:
    """Classify a user message as SIMPLE or COMPLEX via a cheap LLM call.

    Fail-safe: any error, timeout, or unparseable response defaults to
    SIMPLE. We fail toward the FAST path, never toward the EXPENSIVE path —
    an unnecessary MCTS run is much costlier than an occasional under-planned
    simple response.
    """
    try:
        messages = [
            {"role": "system", "content": _CLASSIFIER_SYSTEM_PROMPT},
            {"role": "user", "content": message},
        ]
        chunks: list[str] = []
        async for delta in adapter.stream(messages, max_tokens=10, temperature=0.0):
            chunks.append(delta)
        raw = "".join(chunks).strip().upper()
        if "COMPLEX" in raw:
            return TaskComplexity.COMPLEX
        return TaskComplexity.SIMPLE
    except Exception:
        return TaskComplexity.SIMPLE
