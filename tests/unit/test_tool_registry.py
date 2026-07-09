"""Unit tests for the ToolRegistry class."""

from __future__ import annotations
import pytest
from app.tools.base import BaseTool, ToolResult
from app.tools.registry import ToolRegistry


class DummyTool(BaseTool):
    """A dummy tool implementation for testing purposes."""

    name: str = "dummy"
    description: str = "A dummy tool for testing."
    parameters_schema: dict[str, str] = {"arg1": "first argument", "arg2": "second argument"}

    async def execute(self, *, arg1: str = "", arg2: str = "", **kwargs: str) -> ToolResult:
        """Execute the dummy logic."""
        return ToolResult(
            tool_name=self.name,
            success=True,
            output=f"arg1={arg1}, arg2={arg2}",
        )


@pytest.mark.asyncio
async def test_register_and_get_tool() -> None:
    """Test registering a tool and retrieving it by name."""
    registry = ToolRegistry()
    tool = DummyTool()
    registry.register(tool)
    assert registry.get("dummy") is tool
    assert registry.get("nonexistent") is None
    assert tool in registry.all_tools()


@pytest.mark.asyncio
async def test_execute_unknown_tool_returns_error_result() -> None:
    """Test that executing an unregistered tool returns an error ToolResult instead of raising."""
    registry = ToolRegistry()
    res = await registry.execute("unknown", {"param": "val"})
    assert not res.success
    assert res.tool_name == "unknown"
    assert "Unknown tool" in res.error


@pytest.mark.asyncio
async def test_tool_descriptions_for_prompt_formats_correctly() -> None:
    """Test the tool descriptions formatting for injection in system prompt."""
    registry = ToolRegistry()
    assert registry.tool_descriptions_for_prompt() == "No tools available."

    tool = DummyTool()
    registry.register(tool)
    desc = registry.tool_descriptions_for_prompt()
    assert "Available tools:" in desc
    assert "- dummy(arg1: first argument, arg2: second argument): A dummy tool for testing." in desc


@pytest.mark.asyncio
async def test_execute_calls_tool_and_returns_result() -> None:
    """Test that registry execute() successfully dispatches to the tool."""
    registry = ToolRegistry()
    tool = DummyTool()
    registry.register(tool)
    res = await registry.execute("dummy", {"arg1": "hello", "arg2": "world"})
    assert res.success
    assert res.tool_name == "dummy"
    assert res.output == "arg1=hello, arg2=world"
    assert res.error == ""
