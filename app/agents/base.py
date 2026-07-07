"""Base agent class coordinating model streaming and session state."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.memory.chroma import add_memory, search_memories

if TYPE_CHECKING:
    from app.core.session import Session
    from app.core.ws_hub import WSHub
    from app.models.base import ModelAdapter

_MEMORY_PREFIX = "Relevant context from past conversations:\n"


class BaseAgent:
    """Standard conversational agent that communicates via WebSocket hub."""

    def __init__(self, adapter: ModelAdapter) -> None:
        """Initialize the BaseAgent with a ModelAdapter.

        Args:
            adapter: The model adapter to use for generation.
        """
        self.adapter = adapter

    async def run(
        self,
        session: Session,
        message: str,
        hub: WSHub,
        send_done: bool = True,
    ) -> None:
        """Execute the agent loop: recall memories, stream response, persist turns.

        Args:
            session: The user Session instance.
            message: The user's inbound text message.
            hub: The WebSocket connection hub for broadcasting.
            send_done: Whether to broadcast the done event when finished.
        """
        session.is_running = True
        session.cancel_requested = False
        session.history.append({"role": "user", "content": message})

        # ── Memory recall: inject cross-session context ─────────────
        # Remove any previously-injected memory context (prevent accumulation)
        session.history = [
            m for m in session.history
            if not (
                m.get("role") == "system"
                and m.get("content", "").startswith(_MEMORY_PREFIX)
            )
        ]

        memories = await search_memories(session.user_id, message, n_results=3)
        if memories:
            context = "\n".join(f"- {m}" for m in memories)
            session.history.insert(0, {
                "role": "system",
                "content": f"{_MEMORY_PREFIX}{context}",
            })

        completed_successfully = False
        full_response = ""
        try:
            # Explicitly disable thinking mode (ADR-012) to avoid latency inflation
            # and token starvation/truncation, since reasoning is not surfaced in UI.
            async for delta in self.adapter.stream(session.history, think=False):
                if session.cancel_requested:
                    break
                full_response += delta
                await hub.send_stream(session.id, delta)

            # Record final assistant response in history
            session.history.append({"role": "assistant", "content": full_response})
            if send_done:
                await hub.send_done(session.id, {"prompt_tokens": 0, "completion_tokens": 0})
            if not session.cancel_requested:
                completed_successfully = True
        except Exception as e:
            await hub.send_error(session.id, str(e))
        finally:
            session.is_running = False

        # ── Memory persistence: store both turns ────────────────────
        await add_memory(session.user_id, session.id, "user", message)
        if completed_successfully:
            await add_memory(session.user_id, session.id, "assistant", full_response)

