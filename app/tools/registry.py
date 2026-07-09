"""Singleton registry of all available agent tools."""

from __future__ import annotations
from app.tools.base import BaseTool, ToolResult


class ToolRegistry:
    """Registry managing available tools and their dispatching.

    BaseAgent queries this registry to build tool-use prompts
    and to invoke registered tools.
    """

    def __init__(self) -> None:
        """Initialize the registry with an empty dictionary of tools."""
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Register a new tool.

        Args:
            tool: The tool instance to register.
        """
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool | None:
        """Get a tool by name.

        Args:
            name: The tool name.

        Returns:
            The BaseTool instance or None.
        """
        return self._tools.get(name)

    def all_tools(self) -> list[BaseTool]:
        """Return a list of all registered tools.

        Returns:
            List of BaseTool instances.
        """
        return list(self._tools.values())

    def tool_descriptions_for_prompt(self) -> str:
        """Format the registered tools list for inclusion in LLM prompt.

        Returns:
            Formatted tools description string.
        """
        if not self._tools:
            return "No tools available."
        lines = ["Available tools:"]
        for tool in self._tools.values():
            params = ", ".join(
                f"{k}: {v}" for k, v in tool.parameters_schema.items()
            )
            lines.append(f"- {tool.name}({params}): {tool.description}")
        return "\n".join(lines)

    async def execute(self, name: str, kwargs: dict[str, str]) -> ToolResult:
        """Execute a named tool asynchronously.

        Returns an error ToolResult if the tool is not found.
        Catches any execution exceptions and wraps them in a failed ToolResult.

        Args:
            name: The name of the tool to execute.
            kwargs: Dictionary of keyword arguments for the tool.

        Returns:
            The ToolResult.
        """
        tool = self._tools.get(name)
        if tool is None:
            return ToolResult(
                tool_name=name,
                success=False,
                output="",
                error=f"Unknown tool: '{name}'. Available: {list(self._tools.keys())}",
            )
        try:
            return await tool.execute(**kwargs)
        except Exception as e:
            return ToolResult(
                tool_name=name, success=False, output="", error=str(e)
            )


# Module-level singleton
tool_registry: ToolRegistry = ToolRegistry()
