"""Session Manager to handle isolated user sessions and agent runs."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from app.core.ws_hub import ws_hub
from app.models.ollama import OllamaAdapter
from app.agents.base import BaseAgent
from app.agents.classifier import classify_task, TaskComplexity
from app.agents.mcts import MCTSPlanner
from app.agents.verify import verify_plan_result
from app.agents.hydra import HydraCoordinator
from app.memory.chroma import add_memory


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

        Executes the agent logic: classifies task complexity, then either runs direct
        or routes through MCTS planning followed by verification.

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
            adapter = OllamaAdapter()
            agent = BaseAgent(adapter)
            message = payload.get("message", "")

            # Step 1: classify
            complexity = await classify_task(adapter, message)

            if complexity == TaskComplexity.SIMPLE:
                # Fast path — unchanged from Phase 2
                await agent.run(session, message, ws_hub)

            else:
                # MCTS path
                # Step 2: notify user that planning is in progress
                await ws_hub.send_planning(session_id, "planning")
                await ws_hub.send_stream(
                    session_id,
                    "\n🔍 *Complex task detected — planning steps...*\n\n"
                )

                # Step 3: run MCTS search
                planner = MCTSPlanner(adapter, max_depth=5, max_iterations=20)
                plan = await planner.search(message)

                if not plan:
                    # Search exhausted without finding plan — fall back to direct
                    await ws_hub.send_stream(
                        session_id,
                        "⚠️ *Could not build a plan — attempting direct response.*\n\n"
                    )
                    await agent.run(session, message, ws_hub)
                else:
                    # Step 4: show plan to user before executing
                    plan_text = "\n".join(f"{i+1}. {step}" for i, step in enumerate(plan))
                    await ws_hub.send_stream(
                        session_id,
                        f"📋 *Plan:*\n{plan_text}\n\n"
                    )

                    # Step 5: run plan via HydraCoordinator
                    coordinator = HydraCoordinator()
                    result = await coordinator.run(
                        plan, message, adapter, ws_hub, session_id
                    )

                    # Stream aggregated result to user
                    await ws_hub.send_stream(
                        session_id, f"\n---\n\n{result}"
                    )

                    # Store aggregated result in session history and memory
                    session.history.append({"role": "user", "content": message})
                    session.history.append({"role": "assistant", "content": result})

                    await add_memory(session.user_id, session.id, "user", message)
                    await add_memory(session.user_id, session.id, "assistant", result)

                    # Step 6: verify the result (aggregated coordinator output)
                    try:
                        verification = await verify_plan_result(
                            adapter, message, result
                        )
                        if not verification.passed:
                            await ws_hub.send_stream(
                                session_id,
                                f"\n⚠️ *Verification note: {verification.reason}*\n"
                            )
                    except Exception:
                        pass  # verification is best-effort, never block done event
                    finally:
                        await ws_hub.send_done(
                            session_id, {"prompt_tokens": 0, "completion_tokens": 0}
                        )

        except Exception as e:
            await ws_hub.send_error(session_id, str(e))
        finally:
            session.is_running = False


# Singleton — one session manager per process
session_manager: SessionManager = SessionManager()
