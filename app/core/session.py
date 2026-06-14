"""Session Manager to handle isolated user sessions and agent runs."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from app.core.ws_hub import ws_hub


@dataclass
class Session:
    """Represents an active user session state.

    Attributes:
        id: The unique identifier of the session.
        user_id: The ID of the owner of this session.
        history: The interaction history.
        is_running: Flag indicating if an agent execution is in progress.
        cancel_requested: Flag indicating if a cancellation was requested.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    history: list[dict[str, str]] = field(default_factory=list)
    is_running: bool = False
    cancel_requested: bool = False


class SessionManager:
    """Manages active sessions and coordinates agent execution runs."""

    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}

    def create(self, user_id: str) -> Session:
        """Create a new session with a unique ID for a user.

        Args:
            user_id: The user ID.

        Returns:
            The created Session object.
        """
        session = Session(user_id=user_id)
        self._sessions[session.id] = session
        return session

    def get(self, session_id: str) -> Session | None:
        """Retrieve a session by its session ID.

        Args:
            session_id: The ID of the session to get.

        Returns:
            The Session object if found, otherwise None.
        """
        return self._sessions.get(session_id)

    def get_or_create(self, session_id: str, user_id: str) -> Session:
        """Retrieve a session, or create it with the specified ID if not present.

        Args:
            session_id: The desired session ID.
            user_id: The user ID.

        Returns:
            The existing or newly created Session object.
        """
        if session_id not in self._sessions:
            session = Session(id=session_id, user_id=user_id)
            self._sessions[session_id] = session
        return self._sessions[session_id]

    async def cancel(self, session_id: str) -> None:
        """Request cancellation for an active session task.

        Args:
            session_id: The ID of the session to cancel.
        """
        session = self.get(session_id)
        if session:
            session.cancel_requested = True

    async def handle_task(self, session_id: str, payload: dict[str, Any]) -> None:
        """Process an incoming task message.

        Executes the stub agent logic, streaming back the response.

        Args:
            session_id: The ID of the session.
            payload: The dictionary task payload from the client.
        """
        session = self.get(session_id)
        if not session or session.is_running:
            return

        session.is_running = True
        session.cancel_requested = False

        try:
            # Phase 1 stub: send_stream "Echo: {message}", then send_done
            message = payload.get("message", "")
            await ws_hub.send_stream(session_id, f"Echo: {message}")
            await ws_hub.send_done(session_id, {"prompt_tokens": 0, "completion_tokens": 0})
        except Exception as e:
            await ws_hub.send_error(session_id, str(e))
        finally:
            session.is_running = False


# Singleton — one session manager per process
session_manager: SessionManager = SessionManager()
