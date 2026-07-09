"""Browser automation tool for reading webpage content using Playwright.

Note: Uses the synchronous Playwright API executed in a thread pool because
Python 3.14 on Windows uses WindowsProactorEventLoop which does not support
asyncio.create_subprocess_exec (required by async Playwright). Running sync
Playwright in asyncio.to_thread sidesteps this limitation entirely.
"""

from __future__ import annotations
import asyncio
from app.tools.base import BaseTool, ToolResult

MAX_CHARS = 8000  # prevent context overflow


def _fetch_page_sync(url: str) -> str:
    """Fetch and extract text from a webpage using sync Playwright.

    Args:
        url: The full HTTPS URL to load.

    Returns:
        Cleaned page text, truncated to MAX_CHARS.

    Raises:
        Exception: Any Playwright or network error.
    """
    from playwright.sync_api import sync_playwright  # lazy import
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, timeout=20000, wait_until="domcontentloaded")
        text = page.inner_text("body")
        browser.close()

    cleaned = "\n".join(
        line.strip() for line in text.splitlines() if line.strip()
    )
    if len(cleaned) > MAX_CHARS:
        cleaned = cleaned[:MAX_CHARS] + f"\n\n[Truncated at {MAX_CHARS} chars]"
    return cleaned


class BrowserTool(BaseTool):
    """Tool that fetches and extracts text content from web pages using headless Chromium."""

    name: str = "read_webpage"
    description: str = (
        "Fetch and read the full text content of a webpage. Use after "
        "web_search when you need the complete content of a specific URL."
    )
    parameters_schema: dict[str, str] = {"url": "The full URL to read (must start with https://)"}

    async def execute(self, *, url: str = "", **kwargs: str) -> ToolResult:
        """Execute the webpage text extraction.

        Runs sync Playwright in a thread pool to avoid ProactorEventLoop
        incompatibility on Python 3.14 / Windows.

        Args:
            url: The full URL to load.
            **kwargs: Extra parameters (ignored).

        Returns:
            The ToolResult.
        """
        if not url.strip():
            return ToolResult(
                tool_name=self.name,
                success=False,
                output="",
                error="URL cannot be empty",
            )

        if not url.startswith("https://"):
            return ToolResult(
                tool_name=self.name,
                success=False,
                output="",
                error="URL must start with https://",
            )

        try:
            cleaned = await asyncio.to_thread(_fetch_page_sync, url)
            return ToolResult(
                tool_name=self.name,
                success=True,
                output=cleaned,
            )
        except Exception as e:
            err_str = str(e)
            if (
                "executable" in err_str.lower()
                or "playwright install" in err_str.lower()
                or ("browser" in err_str.lower() and "not" in err_str.lower())
            ):
                err_str = (
                    "Playwright browser not installed. Run: playwright install chromium"
                )
            return ToolResult(
                tool_name=self.name,
                success=False,
                output="",
                error=err_str,
            )
