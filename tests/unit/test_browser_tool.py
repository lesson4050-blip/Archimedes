"""Unit tests for the BrowserTool class."""

from __future__ import annotations
from unittest.mock import MagicMock, patch
import pytest

from app.tools.browser import BrowserTool


@pytest.mark.asyncio
async def test_browser_tool_rejects_non_https_url() -> None:
    """Test that BrowserTool rejects non-HTTPS URLs."""
    tool = BrowserTool()
    res = await tool.execute(url="http://example.com")
    assert not res.success
    assert "URL must start with https://" in res.error


@pytest.mark.asyncio
async def test_browser_tool_rejects_empty_url() -> None:
    """Test that BrowserTool rejects empty or whitespace-only URLs."""
    tool = BrowserTool()
    res = await tool.execute(url="")
    assert not res.success
    assert "URL cannot be empty" in res.error

    res = await tool.execute(url="   ")
    assert not res.success
    assert "URL cannot be empty" in res.error


@pytest.mark.asyncio
async def test_browser_tool_handles_playwright_error_gracefully() -> None:
    """Test that BrowserTool handles Playwright errors and returns a failed ToolResult.

    Patches _fetch_page_sync directly (the sync helper that runs in a thread)
    because BrowserTool now uses sync_playwright via asyncio.to_thread.
    """
    with patch("app.tools.browser._fetch_page_sync", side_effect=Exception("Playwright launch failed")):
        tool = BrowserTool()
        res = await tool.execute(url="https://example.com")
        assert not res.success
        assert res.tool_name == "read_webpage"
        assert "Playwright launch failed" in res.error


@pytest.mark.asyncio
async def test_browser_tool_success() -> None:
    """Test a successful webpage text fetch by patching _fetch_page_sync."""
    with patch(
        "app.tools.browser._fetch_page_sync",
        return_value="Hello\nWorld",
    ):
        tool = BrowserTool()
        res = await tool.execute(url="https://example.com")
        assert res.success
        assert res.tool_name == "read_webpage"
        assert res.output == "Hello\nWorld"
