"""Browser automation tool for reading webpage content using Playwright."""

from __future__ import annotations
from app.tools.base import BaseTool, ToolResult

MAX_CHARS = 8000  # prevent context overflow


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
            from playwright.async_api import async_playwright  # lazy import
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.goto(url, timeout=20000, wait_until="domcontentloaded")
                text = await page.inner_text("body")
                await browser.close()

            # Clean up whitespace
            cleaned = "\n".join(
                line.strip() for line in text.splitlines() if line.strip()
            )
            if len(cleaned) > MAX_CHARS:
                cleaned = cleaned[:MAX_CHARS] + f"\n\n[Truncated at {MAX_CHARS} chars]"

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
                or "browser" in err_str.lower()
                and "not" in err_str.lower()
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
