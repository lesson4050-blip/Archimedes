"""ChromaDB-backed semantic memory store for cross-session recall.

This module follows the implementation pattern from ``.agents/skills/chromadb.md``:

- Module-level ``_client`` / ``_collection`` singletons (lazy init)
- Every ChromaDB SDK call wrapped in ``asyncio.to_thread`` to avoid
  blocking the event loop (see skill doc: "CRITICAL: chromadb client
  is SYNCHRONOUS")
- Tenant isolation via ``where={"user_id": ...}`` filter on every query

See also ``docs/DECISIONS.md`` ADR-011 for why we use CPU-based ONNX
embeddings rather than an Ollama embedding model.
"""

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
    """Lazily initialise the ChromaDB client and collection (sync, called via to_thread).

    Returns:
        The global ``conversations`` collection.
    """
    global _client, _collection  # noqa: PLW0603
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
        role: ``"user"`` or ``"assistant"``.
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
        user_id: ONLY return memories belonging to this user.  This is the
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
            metas: list[dict[str, Any]] = results.get("metadatas", [[]])[0]
            docs = [
                d for d, m in zip(docs, metas)
                if m.get("session_id") != exclude_session_id
            ]
        return docs

    return await asyncio.to_thread(_search)
