"""Abstract interface for all model adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator


class ModelAdapter(ABC):
    """Abstract base class for streaming models."""

    @abstractmethod
    def stream(
        self,
        messages: list[dict[str, str]],
        *,
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        """Yield text deltas as they stream from the model.

        Args:
            messages: List of message dictionaries representing conversation history.
            max_tokens: The maximum number of tokens to generate.
            temperature: Sampling temperature for generation.

        Returns:
            An async iterator yielding string tokens (deltas).
        """
        ...
