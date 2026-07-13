"""Specialist worker agent for executing isolated plan steps."""

from __future__ import annotations
import json as _json
import re
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.base import ModelAdapter

from app.agents.hydra import _run_with_semaphore
from app.memory.blackboard import SharedBlackboard, BlackboardEntry
from app.tools.registry import tool_registry

MAX_WORKER_TOOL_ITERATIONS = 3

WORKER_SYSTEM_PROMPT = (
    "You are a specialist agent executing ONE specific task. "
    "Be direct. Output only what is requested for this specific step. "
    "Do not summarize other steps or add commentary. "
    "Always extract any target URLs, file paths, or parameters from the overall task "
    "if they are not explicitly repeated in your specific step description. "
    "For any time-sensitive query (sports, news, events, prices, schedules): "
    "ALWAYS include the current date in your search query to find results "
    "AFTER today, not historical ones. "
    "Example: instead of 'next World Cup 2026 match' "
    "use 'next World Cup 2026 match after [today's date]'."
)


class WorkerAgent:
    """Executes a single plan step, reads prerequisites from blackboard,
    writes result back to blackboard."""

    def __init__(
        self,
        worker_id: str,
        step_index: int,
        step_description: str,
        adapter: ModelAdapter,
        blackboard: SharedBlackboard,
    ) -> None:
        """Initialize the WorkerAgent.

        Args:
            worker_id: Unique string identifier for the worker.
            step_index: The 0-based step index in the plan.
            step_description: The description of this worker's task.
            adapter: ModelAdapter instance to use for inference.
            blackboard: SharedBlackboard instance to read and write.
        """
        self.worker_id = worker_id
        self.step_index = step_index
        self.step_description = step_description
        self.adapter = adapter
        self.blackboard = blackboard

    async def execute(
        self,
        original_task: str,
        dep_indices: set[int],
    ) -> str:
        """Execute this step via a mini ReAct loop and write result to blackboard.

        Runs up to MAX_WORKER_TOOL_ITERATIONS LLM calls. If the model emits a
        TOOL_CALL, the tool is executed silently (no WS events) and the result
        is fed back into the conversation. When the model responds without a
        TOOL_CALL the loop exits and the response is written to the blackboard.

        Args:
            original_task: The original user request.
            dep_indices: The set of step indices that this step depends on.

        Returns:
            The generated response string for this step.
        """
        prereqs = await self.blackboard.read_prerequisites(dep_indices)
        context = ""
        if prereqs:
            context = "Context from previous steps:\n" + "\n".join(prereqs) + "\n\n"

        tool_desc = tool_registry.tool_descriptions_for_prompt()
        tool_suffix = ""
        if tool_registry.all_tools():
            current_date = datetime.now(timezone.utc).strftime("%B %d, %Y")
            tool_suffix = (
                f"\nCurrent Date: {current_date}\n\n"
                f"{tool_desc}\n\n"
                "To use a tool respond with:\n"
                "TOOL_CALL: tool_name\n"
                'PARAMS: {"param": "value"}\n'
                "Otherwise respond directly."
            )

        messages: list[dict[str, str]] = [
            {"role": "system", "content": WORKER_SYSTEM_PROMPT + tool_suffix},
            {
                "role": "user",
                "content": (
                    f"Overall task: {original_task}\n\n"
                    f"{context}"
                    f"Your specific step: {self.step_description}"
                ),
            },
        ]

        full_result = ""
        result_text = ""
        user_snippet = original_task[:80] if original_task else ""
        lang_reminder = (
            f"(The user wrote: \"{user_snippet}\" — "
            "you MUST reply in the SAME language as that message.)"
        ) if user_snippet else ""

        for iteration in range(MAX_WORKER_TOOL_ITERATIONS):
            result_text = await _run_with_semaphore(self.adapter, messages)

            tool_match = re.search(
                r"TOOL_CALL:\s*(\w+)\s+PARAMS:\s*(\{.*?\})",
                result_text,
                re.DOTALL,
            )

            if not tool_match:
                full_result = result_text
                break

            tool_name = tool_match.group(1).strip()
            try:
                params = _json.loads(tool_match.group(2))
            except Exception:
                params = {}

            tool_result = await tool_registry.execute(tool_name, params)

            messages.append({"role": "assistant", "content": result_text})
            tool_result_text = (
                f"Tool '{tool_name}' result:\n{tool_result.output}"
                if tool_result.success
                else f"Tool '{tool_name}' failed: {tool_result.error}"
            )
            messages.append({
                "role": "user",
                "content": (
                    f"{tool_result_text}\n\n{lang_reminder}"
                    if lang_reminder
                    else tool_result_text
                ),
            })
        else:
            # Loop exhausted — force final answer without tools
            exhausted_prompt = (
                "Please summarize what you found so far. "
                "Do not call any more tools. Give a direct answer."
            )
            messages.append({
                "role": "user",
                "content": (
                    f"{exhausted_prompt}\n\n{lang_reminder}"
                    if lang_reminder
                    else exhausted_prompt
                ),
            })
            full_result = await _run_with_semaphore(self.adapter, messages)

        await self.blackboard.write(
            self.step_index,
            BlackboardEntry(
                step_index=self.step_index,
                step_description=self.step_description,
                result=full_result,
                worker_id=self.worker_id,
                completed_at=datetime.now(timezone.utc).isoformat(),
            ),
        )
        return full_result
