"""Base agent class coordinating model streaming and session state."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.session import Session
    from app.core.ws_hub import WSHub
    from app.models.base import ModelAdapter


class BaseAgent:
    """Standard conversational agent that communicates via WebSocket hub."""

    def __init__(self, adapter: ModelAdapter) -> None:
        """Initialize the BaseAgent with a ModelAdapter.

        Args:
            adapter: The model adapter to use for generation.
        """
        self.adapter = adapter

    async def run(self, session: Session, message: str, hub: WSHub) -> None:
        """Execute the agent loop: update history, stream response, and report done/error.

        Args:
            session: The user Session instance.
            message: The user's inbound text message.
            hub: The WebSocket connection hub for broadcasting.
        """
        session.is_running = True
        session.cancel_requested = False
        session.history.append({"role": "user", "content": message})

        full_response = ""
        try:
            async for delta in self.adapter.stream(session.history):
                if session.cancel_requested:
                    break
                full_response += delta
                await hub.send_stream(session.id, delta)

            # Record final assistant response in history
            session.history.append({"role": "assistant", "content": full_response})
            await hub.send_done(session.id, {"prompt_tokens": 0, "completion_tokens": 0})
        except Exception as e:
            await hub.send_error(session.id, str(e))
        finally:
            session.is_running = False
