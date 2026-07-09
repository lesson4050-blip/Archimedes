"""Web search tool — Tavily (primary) with DuckDuckGo fallback.

Priority:
1. If TAVILY_API_KEY is set and valid → use Tavily (best quality, summarised answers).
2. Otherwise → use DuckDuckGo via duckduckgo-search (no API key required).
"""

from __future__ import annotations
import asyncio
import httpx
from app.tools.base import BaseTool, ToolResult
from app.core.config import get_settings


def _ddg_search_sync(query: str, max_results: int = 5) -> str:
    """Run a DuckDuckGo text search synchronously (called via asyncio.to_thread).

    Args:
        query: The search query string.
        max_results: Maximum number of results to return.

    Returns:
        Formatted search results string.
    """
    from duckduckgo_search import DDGS
    with DDGS() as ddgs:
        results = list(ddgs.text(query, max_results=max_results))

    if not results:
        return "No results found."

    lines: list[str] = []
    for r in results:
        lines.append(f"• {r.get('title', 'No title')}")
        lines.append(f"  {r.get('href', '')}")
        body = r.get("body", "")
        if body:
            lines.append(f"  {body[:300]}...")
        lines.append("")
    return "\n".join(lines)


class WebSearchTool(BaseTool):
    """Tool that searches the web via Tavily (if key set) or DuckDuckGo (fallback)."""

    name: str = "web_search"
    description: str = (
        "Search the web for current information. Use when the user asks about "
        "recent events, facts you are uncertain about, or anything requiring "
        "up-to-date information."
    )
    parameters_schema: dict[str, str] = {"query": "The search query string"}

    async def execute(self, *, query: str = "", **kwargs: str) -> ToolResult:
        """Query Tavily (preferred) or DuckDuckGo (fallback) and format results.

        Uses Tavily when TAVILY_API_KEY is present and not the placeholder value.
        Falls back to DuckDuckGo automatically — no API key required.

        Args:
            query: The search query string.
            **kwargs: Extra parameters (ignored).

        Returns:
            The ToolResult.
        """
        if not query.strip():
            return ToolResult(
                tool_name=self.name,
                success=False,
                output="",
                error="query cannot be empty",
            )

        settings = get_settings()
        tavily_key: str = getattr(settings, "tavily_api_key", "") or ""

        # Use Tavily only when a real key is configured (not the placeholder)
        if tavily_key and not tavily_key.startswith("tvly-..."):
            return await self._search_tavily(query, tavily_key)
        return await self._search_ddg(query)

    async def _search_tavily(self, query: str, api_key: str) -> ToolResult:
        """Search using the Tavily API.

        Args:
            query: The search query string.
            api_key: The Tavily API key.

        Returns:
            The ToolResult.
        """
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    "https://api.tavily.com/search",
                    json={
                        "api_key": api_key,
                        "query": query,
                        "max_results": 5,
                        "include_answer": True,
                    },
                )
                resp.raise_for_status()
                data = resp.json()

            lines: list[str] = []
            if data.get("answer"):
                lines.append(f"Summary: {data['answer']}\n")
            for r in data.get("results", [])[:5]:
                lines.append(f"• {r['title']}")
                lines.append(f"  {r['url']}")
                if r.get("content"):
                    lines.append(f"  {r['content'][:300]}...")
                lines.append("")

            return ToolResult(
                tool_name=self.name,
                success=True,
                output="\n".join(lines),
            )
        except httpx.HTTPStatusError as e:
            return ToolResult(
                tool_name=self.name,
                success=False,
                output="",
                error=f"Tavily API error {e.response.status_code}: {e.response.text[:200]}",
            )
        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                success=False,
                output="",
                error=str(e),
            )

    async def _search_ddg(self, query: str) -> ToolResult:
        """Search using DuckDuckGo — no API key required.

        Runs the synchronous DDGS client in a thread pool to stay async-safe,
        matching the same pattern used in BrowserTool.

        Args:
            query: The search query string.

        Returns:
            The ToolResult.
        """
        try:
            output = await asyncio.to_thread(_ddg_search_sync, query, 5)
            return ToolResult(
                tool_name=self.name,
                success=True,
                output=output,
            )
        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                success=False,
                output="",
                error=f"DuckDuckGo search failed: {e}",
            )
