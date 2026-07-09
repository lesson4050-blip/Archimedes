"""Base tool abstractions and result structures."""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ToolResult:
    """Result of a tool execution.

    Attributes:
        tool_name: Unique identifier of the tool.
        success: Whether the tool executed successfully.
        output: Human-readable output.
        error: Non-empty error message only if success is False.
    """
    tool_name: str
    success: bool
    output: str
    error: str = ""


class BaseTool(ABC):
    """Abstract base for all agent tools.

    Attributes:
        name: Unique identifier of the tool, e.g. "web_search".
        description: Description of the tool's purpose, shown to the LLM.
        parameters_schema: Schema map of param_name to description.
    """

    name: str
    description: str
    parameters_schema: dict[str, str]

    @abstractmethod
    async def execute(self, **kwargs: str) -> ToolResult:
        """Execute the tool.

        Never raise exceptions; always return a ToolResult with success=False on error.

        Args:
            **kwargs: Dynamically passed keyword arguments as strings.

        Returns:
            The ToolResult.
        """
        pass
