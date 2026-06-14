"""Ollama model adapter implementation."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

import httpx

from app.core.config import get_settings
from app.models.base import ModelAdapter


class OllamaAdapter(ModelAdapter):
    """Streams tokens from a local Ollama instance."""

    async def stream(
        self,
        messages: list[dict[str, str]],
        *,
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        """Yield text deltas as they stream from Ollama's chat endpoint.

        Args:
            messages: List of message dictionaries representing conversation history.
            max_tokens: The maximum number of tokens to generate.
            temperature: Sampling temperature for generation.

        Returns:
            An async iterator yielding string tokens (deltas).

        Raises:
            RuntimeError: If Ollama is unavailable or model is missing.
        """
        settings = get_settings()
        url = f"{settings.ollama_base_url}/api/chat"
        payload = {
            "model": settings.local_model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream("POST", url, json=payload) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line.strip():
                            continue
                        data = json.loads(line)
                        delta = data.get("message", {}).get("content", "")
                        if delta:
                            yield delta
                        if data.get("done"):
                            break
        except httpx.ConnectError as e:
            raise RuntimeError(
                "Ollama not available. Start it with: ollama serve\n"
                f"Expected at: {settings.ollama_base_url}"
            ) from e
        except httpx.HTTPStatusError as e:
            raise RuntimeError(
                f"Ollama returned {e.response.status_code}. "
                f"Is model '{settings.local_model}' pulled? "
                f"Run: ollama pull {settings.local_model}"
            ) from e
