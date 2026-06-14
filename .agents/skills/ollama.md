# Skill: Ollama Integration

## Trigger
Use when working on app/models/ollama.py, any LLM adapter, or anything
that calls a local model via Ollama API.

---

## Our Ollama Setup

```
Model:    qwen3:14b (Q4_K_M quantization)
Hardware: RTX 3060 12GB — full GPU inference, no CPU offload
Endpoint: http://localhost:11434 (from OLLAMA_BASE_URL in .env)
API:      OpenAI-compatible + native Ollama API
```

Upgrade path (when RTX 3090 24GB arrives):
- Change LOCAL_MODEL=qwen3:30b-a3b in .env
- Zero code changes needed

---

## API Reference

### Chat endpoint (streaming)

```
POST http://localhost:11434/api/chat
Content-Type: application/json

{
  "model": "qwen3:14b",
  "messages": [
    {"role": "system", "content": "You are Archimedes..."},
    {"role": "user", "content": "hello"}
  ],
  "stream": true,
  "options": {
    "temperature": 0.7,
    "num_predict": 2048
  }
}
```

### Response format (NDJSON — one JSON object per line)

```
{"model":"qwen3:14b","message":{"role":"assistant","content":"Hello"},"done":false}
{"model":"qwen3:14b","message":{"role":"assistant","content":"!"},"done":false}
{"model":"qwen3:14b","message":{"role":"assistant","content":""},"done":true,"eval_count":12}
```

Extract delta from each line: `data["message"]["content"]`
Stop streaming when: `data["done"] == True`

---

## Correct Implementation Pattern

```python
# app/models/ollama.py
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
```

---

## Critical Rules

### NDJSON parsing — do this correctly

```python
# CORRECT: parse each line independently
async for line in response.aiter_lines():
    if not line.strip():
        continue          # skip empty lines between chunks
    data = json.loads(line)
    delta = data["message"]["content"]

# WRONG: never do this
full_text = await response.text()
data = json.loads(full_text)   # fails — not valid JSON, it's NDJSON
```

### Timeout — always 120 seconds

```python
# CORRECT
httpx.AsyncClient(timeout=120.0)

# WRONG — default 5s timeout kills long generations
httpx.AsyncClient()
```

### Error messages must be actionable

```python
# CORRECT — tells user exactly what to do
raise RuntimeError("Ollama not available. Start it with: ollama serve")
raise RuntimeError(f"Model not found. Run: ollama pull {model}")

# WRONG — useless
raise RuntimeError("Connection failed")
```

### Never swallow ConnectError silently

```python
# WRONG
try:
    ...
except Exception:
    pass

# CORRECT — surface the error with context
except httpx.ConnectError as e:
    raise RuntimeError("Ollama not available...") from e
```

---

## Testing Ollama Code

### Mock pattern for unit tests

```python
# tests/unit/test_ollama_adapter.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.models.ollama import OllamaAdapter
import httpx

@pytest.mark.asyncio
async def test_streams_deltas() -> None:
    """Adapter yields content from each NDJSON line."""
    lines = [
        b'{"message":{"content":"Hello"},"done":false}\n',
        b'{"message":{"content":" world"},"done":false}\n',
        b'{"message":{"content":""},"done":true}\n',
    ]

    mock_response = AsyncMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.aiter_lines = AsyncMock(
        return_value=iter([line.decode() for line in lines])
    )

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.stream.return_value.__aenter__ = AsyncMock(
            return_value=mock_response
        )
        adapter = OllamaAdapter()
        deltas = [d async for d in adapter.stream([{"role": "user", "content": "hi"}])]

    assert deltas == ["Hello", " world"]

@pytest.mark.asyncio
async def test_raises_on_connect_error() -> None:
    """ConnectError becomes a RuntimeError with actionable message."""
    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__ = AsyncMock(
            side_effect=httpx.ConnectError("refused")
        )
        adapter = OllamaAdapter()
        with pytest.raises(RuntimeError, match="ollama serve"):
            async for _ in adapter.stream([{"role": "user", "content": "hi"}]):
                pass
```

---

## Useful Ollama CLI Commands

```bash
ollama serve              # start Ollama server
ollama list               # list downloaded models
ollama pull qwen3:14b     # download our model
ollama ps                 # show running models + VRAM usage
ollama rm <model>         # remove a model

# Test model directly
ollama run qwen3:14b "Hello, who are you?"

# Check VRAM usage during inference
ollama ps
# NAME          ID       SIZE    PROCESSOR  UNTIL
# qwen3:14b     abc123   9.1 GB  100% GPU   forever
```
