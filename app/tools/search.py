"""Web search tool — Tavily (primary) with DuckDuckGo fallback.

Priority:
1. If TAVILY_API_KEY is set and valid → use Tavily (best quality, summarised answers).
2. Otherwise → use DuckDuckGo text API (fast fallback).
3. If DuckDuckGo text API returns empty or fails → use DuckDuckGo HTML scraper (extremely robust).
"""

from __future__ import annotations
import asyncio
import urllib.parse
import httpx
from bs4 import BeautifulSoup
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
        # Trigger fallback to HTML scraper if empty
        return _ddg_html_search_sync(query, max_results)

    lines: list[str] = []
    for r in results:
        lines.append(f"• {r.get('title', 'No title')}")
        lines.append(f"  {r.get('href', '')}")
        body = r.get("body", "")
        if body:
            lines.append(f"  {body[:300]}...")
        lines.append("")
    return "\n".join(lines)


def _ddg_html_search_sync(query: str, max_results: int = 5) -> str:
    """Fallback DuckDuckGo scraper using the public HTML interface.

    Extremely reliable even when API clients are rate-limited or blocked.

    Args:
        query: The search query string.
        max_results: Maximum number of results.

    Returns:
        Formatted search results.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }
    url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
    
    # Run sync request
    with httpx.Client(timeout=12.0) as client:
        resp = client.get(url, headers=headers)
        resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    results = []
    for a in soup.find_all("a", class_="result__snippet"):
        parent = a.find_parent("div", class_="result__body")
        if parent:
            title_a = parent.find("a", class_="result__url")
            if title_a:
                href = str(title_a.get("href") or "")
                # Parse redirect link if present
                if "uddg=" in href:
                    parsed = urllib.parse.urlparse(href)
                    qs = urllib.parse.parse_qs(parsed.query)
                    actual_url = qs.get("uddg", [href])[0]
                else:
                    actual_url = href

                results.append({
                    "title": title_a.text.strip(),
                    "href": actual_url,
                    "body": a.text.strip()
                })

    if not results:
        return "No results found."

    lines: list[str] = []
    for r in results[:max_results]:
        lines.append(f"• {r['title']}")
        lines.append(f"  {r['href']}")
        lines.append(f"  {r['body'][:300]}...")
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

        Automatically appends the current date to every query so that
        time-sensitive searches (sports, news, prices) always return
        fresh results — even when the LLM forgets to include the date.

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

        # Programmatically inject current date into query so search
        # engines prioritise fresh results. The LLM often forgets to
        # include the date despite being told to in the system prompt.
        from datetime import datetime, timezone

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if today not in query:
            query = f"{query} {today}"

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

        Runs the synchronous DDGS client / HTML scraper in a thread pool to stay
        async-safe.

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
            # If the library completely fails, try the HTML scraper directly
            try:
                output = await asyncio.to_thread(_ddg_html_search_sync, query, 5)
                return ToolResult(
                    tool_name=self.name,
                    success=True,
                    output=output,
                )
            except Exception as inner_e:
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    output="",
                    error=f"DuckDuckGo search failed: {e}. Fallback failed: {inner_e}",
                )
