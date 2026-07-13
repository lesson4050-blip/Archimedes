"""Base agent class coordinating model streaming and session state."""

from __future__ import annotations

from datetime import datetime
import json
import re
from typing import TYPE_CHECKING

from app.memory.chroma import add_memory, search_memories

if TYPE_CHECKING:
    from app.core.session import Session
    from app.core.ws_hub import WSHub
    from app.models.base import ModelAdapter

_MEMORY_PREFIX = "Relevant context from past conversations:\n"

SYSTEM_PROMPT = (
    "You are Archimedes, an autonomous AI agent. "
    "Be direct and concise. No filler phrases, no emojis. "
    "When executing a plan, focus on the task. "
    "ALWAYS respond in the same language the user writes in — this applies "
    "to ALL responses including error messages and 'not found' replies. "
    "If a tool returns no results or empty data, tell the user in their "
    "language that you could not find the information. "
    "NEVER invent numbers, facts, or URLs when search returns nothing."
)

TOOL_USE_PROMPT_SUFFIX = """
{tool_descriptions}

For any time-sensitive query (sports, news, events, prices, schedules):
ALWAYS include the current date in your search query to find results
AFTER today, not historical ones.
Example: instead of 'next World Cup 2026 match'
use 'next World Cup 2026 match after [today's date]'

To use a tool, respond with EXACTLY this format (no other text before it):
TOOL_CALL: tool_name
PARAMS: {{"param_name": "value"}}

After receiving tool results, continue your response normally.
If you don't need any tools, respond directly without the TOOL_CALL prefix.
IMPORTANT: Always reply in the same language the user used.
"""

MAX_TOOL_ITERATIONS = 5


class BaseAgent:
    """Standard conversational agent that communicates via WebSocket hub."""

    def __init__(self, adapter: ModelAdapter) -> None:
        """Initialize the BaseAgent with a ModelAdapter.

        Args:
            adapter: The model adapter to use for generation.
        """
        self.adapter = adapter

    async def _run_react_loop(
        self,
        messages: list[dict[str, str]],
        session: Session,
        hub: WSHub,
    ) -> str:
        """Run the ReAct loop: LLM calls tools until it has enough info to answer.

        Args:
            messages: The initial messages list (including system prompt).
            session: The active Session instance.
            hub: The WebSocket hub for event broadcasting.

        Returns:
            The final response string from the agent.
        """
        from app.tools.registry import tool_registry

        tool_messages = list(messages)  # copy — don't mutate session history
        full_response = ""

        for iteration in range(MAX_TOOL_ITERATIONS):
            chunks: list[str] = []
            async for delta in self.adapter.stream(tool_messages, think=False):
                if session.cancel_requested:
                    break
                chunks.append(delta)
            response_text = "".join(chunks)

            # Detect tool call
            tool_match = re.search(
                r"TOOL_CALL:\s*(\w+)\s+PARAMS:\s*(\{.*?\})",
                response_text,
                re.DOTALL,
            )

            if not tool_match:
                # Stream already-collected chunks — no second LLM call
                # chunks contains the real token deltas from the first stream() call
                for chunk in chunks:
                    if session.cancel_requested:
                        break
                    await hub.send_stream(session.id, chunk)
                full_response = response_text
                break

            tool_name = tool_match.group(1).strip()
            try:
                params = json.loads(tool_match.group(2))
            except Exception:
                params = {}

            # Stream tool_call event to frontend
            await hub.broadcast(session.id, {
                "type": "tool_call",
                "session_id": session.id,
                "payload": {"tool": tool_name, "input": params},
            })

            # Execute tool
            result = await tool_registry.execute(tool_name, params)

            # Stream tool_result event to frontend
            await hub.broadcast(session.id, {
                "type": "tool_result",
                "session_id": session.id,
                "payload": {
                    "tool": tool_name,
                    "success": result.success,
                    "output": result.output if result.success else result.error,
                },
            })

            # Inject result into conversation for next iteration
            tool_messages.append({"role": "assistant", "content": response_text})
            tool_result_text = (
                f"Tool '{tool_name}' result:\n{result.output}"
                if result.success
                else f"Tool '{tool_name}' failed: {result.error}"
            )
            tool_messages.append({
                "role": "user",
                "content": (
                    f"{tool_result_text}\n\n"
                    "(Remember: reply in the same language the user used.)"
                ),
            })

            if session.cancel_requested:
                break
        else:
            # Hit MAX_TOOL_ITERATIONS — return what we have
            full_response = full_response

        return full_response

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
            from app.tools.registry import tool_registry

            tool_desc = tool_registry.tool_descriptions_for_prompt()
            current_date_str = datetime.now().strftime("%B %d, %Y")
            system_content = f"{SYSTEM_PROMPT}\n\nCurrent Date: {current_date_str}"
            if tool_registry.all_tools():
                system_content += f"\n\n{TOOL_USE_PROMPT_SUFFIX.format(tool_descriptions=tool_desc)}"

            messages = [
                {"role": "system", "content": system_content},
                *session.history,
            ]

            if tool_registry.all_tools():
                full_response = await self._run_react_loop(messages, session, hub)
            else:
                async for delta in self.adapter.stream(messages, think=False):
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


