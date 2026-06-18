# Skill: ChromaDB Memory

## Trigger
Use when working on app/memory/, semantic search, embeddings, persistent
memory, cross-session recall, or anything calling chromadb.

---

## Our Setup

```
Mode:       PersistentClient (local embedded, no server)
Path:       get_settings().chroma_path  (./data/chroma_db)
Embedding:  ChromaDB default function (ONNX MiniLM-L6-v2, runs on CPU)
Collection: single global "conversations" collection
Tenancy:    metadata filter on user_id (NOT per-user collections)
```

**Why CPU embedding, not Ollama:** an Ollama embedding model would compete
for VRAM with qwen3:14b (RTX 3060 12GB is nearly full already) and force
Ollama to swap models in/out on every turn, adding latency. See
docs/DECISIONS.md ADR-011.

---

## CRITICAL: chromadb client is SYNCHRONOUS

The Python SDK blocks the calling thread. If you call it directly inside
an `async def`, you freeze the event loop for the ENTIRE app — every
WebSocket session stalls, not just the one doing the memory lookup.

```python
# WRONG — blocks the event loop for all sessions
def search(query: str) -> list[str]:
    results = collection.query(query_texts=[query], n_results=5)
    return results["documents"][0]

# CORRECT — always wrap in asyncio.to_thread
async def search(query: str) -> list[str]:
    results = await asyncio.to_thread(
        collection.query, query_texts=[query], n_results=5
    )
    return results["documents"][0]
```

This applies to EVERY chromadb call: `.add()`, `.query()`, `.get()`, `.delete()`.

---

## Implementation Pattern

```python
# app/memory/chroma.py
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any

import chromadb
from chromadb.api.models.Collection import Collection

from app.core.config import get_settings

_client: chromadb.ClientAPI | None = None
_collection: Collection | None = None


def _get_collection() -> Collection:
    """Lazily initialise the ChromaDB client and collection (sync, called via to_thread)."""
    global _client, _collection
    if _collection is None:
        settings = get_settings()
        _client = chromadb.PersistentClient(path=settings.chroma_path)
        _collection = _client.get_or_create_collection("conversations")
    return _collection


async def add_memory(
    user_id: str,
    session_id: str,
    role: str,
    content: str,
) -> None:
    """Store one conversation turn as a memory entry.

    Args:
        user_id: Owner of this memory — used for tenant isolation.
        session_id: Which chat session this turn belongs to.
        role: "user" or "assistant".
        content: The message text to embed and store.
    """
    if not content.strip():
        return  # chromadb raises on empty-string embeddings

    def _add() -> None:
        collection = _get_collection()
        collection.add(
            ids=[str(uuid.uuid4())],
            documents=[content],
            metadatas=[{
                "user_id": user_id,
                "session_id": session_id,
                "role": role,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }],
        )

    await asyncio.to_thread(_add)


async def search_memories(
    user_id: str,
    query: str,
    *,
    n_results: int = 5,
    exclude_session_id: str | None = None,
) -> list[str]:
    """Semantic search over a user's past memories.

    Args:
        user_id: ONLY return memories belonging to this user. This is the
            tenant-isolation boundary — never omit this filter.
        query: Text to search for semantically similar past content.
        n_results: Max number of results to return.
        exclude_session_id: Optionally exclude the current session (useful
            for testing true cross-session recall vs same-session echo).

    Returns:
        List of matched document strings, most relevant first.
    """
    if not query.strip():
        return []

    def _search() -> list[str]:
        collection = _get_collection()
        where: dict[str, Any] = {"user_id": user_id}
        results = collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where,
        )
        docs: list[str] = results.get("documents", [[]])[0]
        if exclude_session_id:
            metas = results.get("metadatas", [[]])[0]
            docs = [
                d for d, m in zip(docs, metas)
                if m.get("session_id") != exclude_session_id
            ]
        return docs

    return await asyncio.to_thread(_search)
```

---

## Integration with BaseAgent

```python
# Inside BaseAgent.run(), BEFORE calling adapter.stream():
memories = await search_memories(session.user_id, message, n_results=3)
if memories:
    context = "\n".join(f"- {m}" for m in memories)
    session.history.insert(0, {
        "role": "system",
        "content": f"Relevant context from past conversations:\n{context}",
    })

# AFTER full response is accumulated, store BOTH turns:
await add_memory(session.user_id, session.id, "user", message)
await add_memory(session.user_id, session.id, "assistant", full_response)
```

Insert the system message at index 0 fresh each turn — don't let it
accumulate duplicated across multiple turns in the same session.

---

## Testing Pattern — use a REAL temp ChromaDB, don't mock the SDK

ChromaDB's internal API surface is non-trivial to mock correctly (query
result shapes, embedding function internals). Use a real `PersistentClient`
pointed at a temp directory instead — it's fast enough for tests.

```python
# tests/unit/test_chroma_store.py
import tempfile
import pytest
from unittest.mock import patch

@pytest.fixture
def temp_chroma_path(tmp_path):
    return str(tmp_path / "test_chroma")

@pytest.fixture(autouse=True)
def reset_chroma_singleton():
    """Reset module-level singletons between tests."""
    import app.memory.chroma as chroma_module
    chroma_module._client = None
    chroma_module._collection = None
    yield
    chroma_module._client = None
    chroma_module._collection = None

@pytest.mark.asyncio
async def test_add_and_search_memory(temp_chroma_path, monkeypatch):
    from app.core.config import get_settings
    monkeypatch.setattr(get_settings(), "chroma_path", temp_chroma_path)

    from app.memory.chroma import add_memory, search_memories
    await add_memory("user-1", "session-a", "user", "My favorite color is teal")
    results = await search_memories("user-1", "what color do I like?")
    assert any("teal" in r for r in results)

@pytest.mark.asyncio
async def test_no_cross_user_leakage(temp_chroma_path, monkeypatch):
    """CRITICAL: user A must never see user B's memories."""
    from app.core.config import get_settings
    monkeypatch.setattr(get_settings(), "chroma_path", temp_chroma_path)

    from app.memory.chroma import add_memory, search_memories
    await add_memory("user-A", "session-1", "user", "My secret project is called Phoenix")
    await add_memory("user-B", "session-2", "user", "I like hiking on weekends")

    results_for_b = await search_memories("user-B", "what is my secret project?")
    assert not any("Phoenix" in r for r in results_for_b)
```

---

## Verify Ownership Before Delete Pattern

When deleting an entry by ID, do not rely solely on `collection.delete(ids=[memory_id])`. Explicitly check ownership first by retrieving the entry with `collection.get` and validating its `user_id` metadata.

```python
async def delete_memory(user_id: str, memory_id: str) -> bool:
    def _delete() -> bool:
        collection = _get_collection()
        res = collection.get(ids=[memory_id])
        if not res.get("ids"):
            return False
        metadatas = res.get("metadatas")
        if not metadatas or not metadatas[0]:
            return False
        meta = metadatas[0]
        if not meta or meta.get("user_id") != user_id:
            return False
        collection.delete(ids=[memory_id])
        return True

    return await asyncio.to_thread(_delete)
```

---

## Common Pitfalls

- **Forgetting `asyncio.to_thread`** → blocks event loop for all sessions, not just one.
- **Forgetting `where={"user_id": ...}`** → real privacy bug, leaks across users. Always test for this explicitly.
- **Embedding empty strings** → chromadb raises `ValueError`. Guard with `.strip()` check before calling `.add()`.
- **Re-inserting the system context message every turn without clearing the old one** → context window fills with duplicate "relevant context" blocks.
- **Missing `onnxruntime` dependency** → `DefaultEmbeddingFunction` raises ImportError on first use if not installed. Verify with: `python -c "from chromadb.utils.embedding_functions import DefaultEmbeddingFunction; DefaultEmbeddingFunction()"` and add the missing package to requirements.txt if it fails.
