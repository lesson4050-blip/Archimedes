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

# chromadb does not export a stable public type for PersistentClient's
# return value across versions — Any is used deliberately here, not as
# a shortcut. Do not replace with a guessed type without verifying it
# against the installed chromadb version.
_client: Any = None
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
        documents = results.get("documents")
        if not documents or not documents[0]:
            return []

        docs = [str(d) for d in documents[0]]

        metadatas = results.get("metadatas")
        if exclude_session_id and metadatas and metadatas[0]:
            metas = metadatas[0]
            docs = [
                d for d, m in zip(docs, metas)
                if m and m.get("session_id") != exclude_session_id
            ]
        return docs

    return await asyncio.to_thread(_search)


async def list_memories(user_id: str, limit: int = 200) -> list[dict[str, str]]:
    """List a user's memories, most recent first.

    Uses collection.get() (not .query()) since this is a filter-based
    listing, not a semantic search.
    Returns dicts with keys: id, content, role, session_id, timestamp.
    Sort by timestamp descending before returning (ISO 8601 strings
    sort correctly as chronological order).
    """
    def _list() -> list[dict[str, str]]:
        collection = _get_collection()
        res = collection.get(where={"user_id": user_id}, limit=limit)
        ids = res.get("ids") or []
        documents = res.get("documents") or []
        metadatas = res.get("metadatas") or []

        entries = []
        for i in range(len(ids)):
            meta = metadatas[i] if i < len(metadatas) and metadatas[i] else {}
            entries.append({
                "id": ids[i],
                "content": documents[i] if i < len(documents) else "",
                "role": str(meta.get("role", "")),
                "session_id": str(meta.get("session_id", "")),
                "timestamp": str(meta.get("timestamp", "")),
            })
        entries.sort(key=lambda x: x["timestamp"], reverse=True)
        return entries

    return await asyncio.to_thread(_list)


async def delete_memory(user_id: str, memory_id: str) -> bool:
    """Delete a memory entry, but ONLY if it belongs to user_id.

    CRITICAL SECURITY STEP — do not skip:
    1. First call collection.get(ids=[memory_id]) to fetch the entry's metadata.
    2. If no entry found, OR metadata["user_id"] != user_id: return False
       WITHOUT calling delete. Do not rely on combining ids+where in a
       single delete() call — explicit ownership check first, always.
    3. Only if ownership is confirmed: call collection.delete(ids=[memory_id])
       and return True.
    """
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
