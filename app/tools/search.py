"""Web search tool utilizing the Tavily API."""

from __future__ import annotations
import httpx
from app.tools.base import BaseTool, ToolResult
from app.core.config import get_settings


class WebSearchTool(BaseTool):
    """Tool that queries the Tavily API for current information."""

    name: str = "web_search"
    description: str = (
        "Search the web for current information. Use when the user asks about "
        "recent events, facts you are uncertain about, or anything requiring "
        "up-to-date information."
    )
    parameters_schema: dict[str, str] = {"query": "The search query string"}

    async def execute(self, *, query: str = "", **kwargs: str) -> ToolResult:
        """Query Tavily search and format the results.

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
        # Retrieve API key dynamically. We check both settings.tavily_api_key
        # and support fallback check to ensure it degrades gracefully.
        tavily_key = getattr(settings, "tavily_api_key", "")
        if not tavily_key:
            return ToolResult(
                tool_name=self.name,
                success=False,
                output="",
                error="TAVILY_API_KEY not set in .env",
            )

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    "https://api.tavily.com/search",
                    json={
                        "api_key": tavily_key,
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
