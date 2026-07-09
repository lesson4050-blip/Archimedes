"""Unit tests for the WebSearchTool class."""

from __future__ import annotations
from unittest.mock import MagicMock, patch, AsyncMock
import httpx
import pytest

from app.tools.search import WebSearchTool
from app.core.config import Settings


@pytest.mark.asyncio
async def test_search_tool_falls_back_to_ddg_when_no_key() -> None:
    """When TAVILY_API_KEY is empty, WebSearchTool falls back to DuckDuckGo."""
    mock_settings = Settings(tavily_api_key="")
    with patch("app.tools.search.get_settings", return_value=mock_settings):
        with patch(
            "app.tools.search._ddg_search_sync",
            return_value="• DDG Result\n  https://ddg.example.com\n",
        ):
            tool = WebSearchTool()
            res = await tool.execute(query="test query")
            assert res.success
            assert "DDG Result" in res.output


@pytest.mark.asyncio
async def test_search_tool_falls_back_to_ddg_when_key_is_placeholder() -> None:
    """When TAVILY_API_KEY is the placeholder value, WebSearchTool uses DuckDuckGo."""
    mock_settings = Settings(tavily_api_key="tvly-...  # Get from app.tavily.com")
    with patch("app.tools.search.get_settings", return_value=mock_settings):
        with patch(
            "app.tools.search._ddg_search_sync",
            return_value="• DDG Result\n  https://ddg.example.com\n",
        ):
            tool = WebSearchTool()
            res = await tool.execute(query="test query")
            assert res.success
            assert "DDG Result" in res.output


@pytest.mark.asyncio
async def test_search_tool_rejects_empty_query() -> None:
    """Test that WebSearchTool rejects empty or whitespace-only queries."""
    tool = WebSearchTool()
    res = await tool.execute(query="")
    assert not res.success
    assert "query cannot be empty" in res.error

    res = await tool.execute(query="   ")
    assert not res.success
    assert "query cannot be empty" in res.error


@pytest.mark.asyncio
async def test_search_tool_formats_tavily_results_correctly() -> None:
    """Test that Tavily response results are formatted correctly with summary and snippets."""
    mock_settings = Settings(tavily_api_key="tvly-mock-key")

    tavily_response_data = {
        "answer": "This is a summary of findings.",
        "results": [
            {
                "title": "Result Title 1",
                "url": "https://example.com/1",
                "content": "This is the content of result 1. " * 20,
            },
            {
                "title": "Result Title 2",
                "url": "https://example.com/2",
                "content": "Short content.",
            },
        ],
    }

    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.json.return_value = tavily_response_data
    mock_resp.raise_for_status = MagicMock()

    with patch("app.tools.search.get_settings", return_value=mock_settings):
        with patch("httpx.AsyncClient.post", return_value=mock_resp) as mock_post:
            tool = WebSearchTool()
            res = await tool.execute(query="my search")
            assert res.success
            assert res.tool_name == "web_search"
            assert "Summary: This is a summary of findings." in res.output
            assert "• Result Title 1" in res.output
            assert "https://example.com/1" in res.output
            assert "• Result Title 2" in res.output
            assert "https://example.com/2" in res.output

            mock_post.assert_called_once()
            called_json = mock_post.call_args[1]["json"]
            assert called_json["api_key"] == "tvly-mock-key"
            assert called_json["query"] == "my search"


@pytest.mark.asyncio
async def test_search_tool_handles_http_error_gracefully() -> None:
    """Test that WebSearchTool handles HTTP status errors from Tavily gracefully."""
    mock_settings = Settings(tavily_api_key="tvly-mock-key")

    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 429
    mock_resp.text = "Rate limit exceeded"
    mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
        message="Too many requests",
        request=MagicMock(spec=httpx.Request),
        response=mock_resp,
    )

    with patch("app.tools.search.get_settings", return_value=mock_settings):
        with patch("httpx.AsyncClient.post", return_value=mock_resp):
            tool = WebSearchTool()
            res = await tool.execute(query="test query")
            assert not res.success
            assert "Tavily API error 429" in res.error
            assert "Rate limit exceeded" in res.error


@pytest.mark.asyncio
async def test_search_tool_ddg_error_returns_failed_result() -> None:
    """When DuckDuckGo search raises, WebSearchTool returns a failed ToolResult."""
    mock_settings = Settings(tavily_api_key="")
    with patch("app.tools.search.get_settings", return_value=mock_settings):
        with patch(
            "app.tools.search._ddg_search_sync",
            side_effect=Exception("network timeout"),
        ), patch(
            "app.tools.search._ddg_html_search_sync",
            side_effect=Exception("html timeout"),
        ):
            tool = WebSearchTool()
            res = await tool.execute(query="test query")
            assert not res.success
            assert "DuckDuckGo search failed" in res.error
            assert "html timeout" in res.error
