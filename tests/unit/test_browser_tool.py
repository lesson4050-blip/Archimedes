"""Unit tests for the BrowserTool class."""

from __future__ import annotations
from unittest.mock import MagicMock, AsyncMock, patch
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
    """Test that BrowserTool handles Playwright errors and returns a failed ToolResult."""
    with patch("playwright.async_api.async_playwright") as mock_playwright:
        mock_playwright.side_effect = Exception("Playwright launch failed")
        tool = BrowserTool()
        res = await tool.execute(url="https://example.com")
        assert not res.success
        assert res.tool_name == "read_webpage"
        assert "Playwright launch failed" in res.error


@pytest.mark.asyncio
async def test_browser_tool_success() -> None:
    """Test a successful webpage text fetch with full mock of the Playwright API."""
    mock_browser = AsyncMock()
    mock_page = AsyncMock()
    mock_page.inner_text.return_value = "   Hello   \n   World   "
    mock_browser.new_page.return_value = mock_page
    
    mock_playwright_instance = AsyncMock()
    mock_playwright_instance.chromium.launch.return_value = mock_browser
    
    mock_playwright_context = MagicMock()
    mock_playwright_context.__aenter__.return_value = mock_playwright_instance
    
    with patch("playwright.async_api.async_playwright", return_value=mock_playwright_context):
        tool = BrowserTool()
        res = await tool.execute(url="https://example.com")
        assert res.success
        assert res.tool_name == "read_webpage"
        assert res.output == "Hello\nWorld"
        mock_page.goto.assert_called_once_with("https://example.com", timeout=20000, wait_until="domcontentloaded")
