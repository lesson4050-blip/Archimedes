# Skill: Tool System + Web Search

## Trigger
Use when working on app/tools/, app/agents/base.py (ReAct loop),
web search integration, browser tool, or anything related to agent
tool use and external data retrieval.

---

## Architecture Overview

```
User message
  → BaseAgent.run()
      → ReAct Loop (max 5 iterations):
          LLM decides: "I need to search for X"
          → ToolRegistry.execute("web_search", {"query": "X"})
          → Result injected into context
          → LLM continues with new information
      → Final answer streamed to user
```

Tool calls and results are streamed to frontend as separate WS events
(already defined in protocol: type="tool_call", type="tool_result").
The frontend renders them as collapsible blocks in the chat.

---

## BaseTool ABC

```python
# app/tools/base.py
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ToolResult:
    """Result of a tool execution."""
    tool_name: str
    success: bool
    output: str          # human-readable result
    error: str = ""      # non-empty only if success=False


class BaseTool(ABC):
    """Abstract base for all agent tools."""

    name: str            # unique identifier, e.g. "web_search"
    description: str     # shown to LLM to decide when to use this tool
    parameters_schema: dict[str, str]  # {"param_name": "description"}

    @abstractmethod
    async def execute(self, **kwargs: str) -> ToolResult:
        """Execute the tool. Never raise — return ToolResult(success=False) on error."""
```

---

## ToolRegistry

```python
# app/tools/registry.py
from __future__ import annotations
from app.tools.base import BaseTool, ToolResult


class ToolRegistry:
    """Singleton registry of all available tools.

    Tools register themselves at module load time. BaseAgent queries
    this to build the tool-use prompt and to dispatch tool calls.
    """

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool | None:
        return self._tools.get(name)

    def all_tools(self) -> list[BaseTool]:
        return list(self._tools.values())

    def tool_descriptions_for_prompt(self) -> str:
        """Format tool list for injection into LLM system prompt."""
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
        """Execute a named tool. Returns error ToolResult if tool not found."""
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
tool_registry = ToolRegistry()
```

---

## Web Search Tool (Tavily)

```python
# app/tools/search.py
from __future__ import annotations
import httpx
from app.tools.base import BaseTool, ToolResult
from app.core.config import get_settings


class WebSearchTool(BaseTool):
    name = "web_search"
    description = (
        "Search the web for current information. Use when the user asks about "
        "recent events, facts you are uncertain about, or anything requiring "
        "up-to-date information."
    )
    parameters_schema = {"query": "The search query string"}

    async def execute(self, *, query: str = "", **_: str) -> ToolResult:
        if not query.strip():
            return ToolResult(
                tool_name=self.name, success=False,
                output="", error="query cannot be empty"
            )
        settings = get_settings()
        if not settings.tavily_api_key:
            return ToolResult(
                tool_name=self.name, success=False, output="",
                error="TAVILY_API_KEY not set in .env"
            )
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    "https://api.tavily.com/search",
                    json={
                        "api_key": settings.tavily_api_key,
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
                tool_name=self.name, success=False, output="",
                error=f"Tavily API error {e.response.status_code}: {e.response.text[:200]}"
            )
        except Exception as e:
            return ToolResult(
                tool_name=self.name, success=False, output="", error=str(e)
            )
```

---

## Browser Tool (Playwright)

```python
# app/tools/browser.py
from __future__ import annotations
from app.tools.base import BaseTool, ToolResult

MAX_CHARS = 8000  # prevent context overflow


class BrowserTool(BaseTool):
    name = "read_webpage"
    description = (
        "Fetch and read the full text content of a webpage. Use after "
        "web_search when you need the complete content of a specific URL."
    )
    parameters_schema = {"url": "The full URL to read (must start with https://)"}

    async def execute(self, *, url: str = "", **_: str) -> ToolResult:
        if not url.startswith("https://"):
            return ToolResult(
                tool_name=self.name, success=False, output="",
                error="URL must start with https://"
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
                tool_name=self.name, success=True, output=cleaned
            )
        except Exception as e:
            return ToolResult(
                tool_name=self.name, success=False, output="", error=str(e)
            )
```

---

## ReAct Loop in BaseAgent

The ReAct (Reason + Act) pattern: LLM reasons about what to do,
acts by calling a tool, observes the result, repeats.

```python
# Additions to app/agents/base.py

TOOL_USE_PROMPT_SUFFIX = """
{tool_descriptions}

To use a tool, respond with EXACTLY this format (no other text before it):
TOOL_CALL: tool_name
PARAMS: {{"param_name": "value"}}

After receiving tool results, continue your response normally.
If you don't need any tools, respond directly without the TOOL_CALL prefix.
"""

MAX_TOOL_ITERATIONS = 5  # hard cap — prevent infinite loops

async def _run_react_loop(
    self,
    messages: list[dict[str, str]],
    session: Session,
    hub: WSHub,
) -> str:
    """ReAct loop: LLM calls tools until it has enough info to answer."""
    import re, json as _json
    from app.tools.registry import tool_registry

    tool_messages = list(messages)  # copy — don't mutate session history
    full_response = ""

    for iteration in range(MAX_TOOL_ITERATIONS):
        chunks: list[str] = []
        async for delta in self.adapter.stream(tool_messages, think=False):
            chunks.append(delta)
        response_text = "".join(chunks)

        # Detect tool call
        tool_match = re.search(
            r"TOOL_CALL:\s*(\w+)\s*\nPARAMS:\s*(\{.*?\})",
            response_text,
            re.DOTALL,
        )

        if not tool_match:
            # No tool call — this is the final answer
            full_response = response_text
            break

        tool_name = tool_match.group(1).strip()
        try:
            params = _json.loads(tool_match.group(2))
        except Exception:
            params = {}

        # Stream tool_call event to frontend
        await hub.broadcast(session.id, {
            "type": "tool_call",
            "session_id": session.id,
            "payload": {"tool": tool_name, "input": params},
        })

        # Execute tool
        result = await tool_registry.execute(tool_name, params)

        # Stream tool_result event to frontend
        await hub.broadcast(session.id, {
            "type": "tool_result",
            "session_id": session.id,
            "payload": {
                "tool": tool_name,
                "success": result.success,
                "output": result.output if result.success else result.error,
            },
        })

        # Inject result into conversation for next iteration
        tool_messages.append({"role": "assistant", "content": response_text})
        tool_messages.append({
            "role": "user",
            "content": (
                f"Tool '{tool_name}' result:\n{result.output}"
                if result.success
                else f"Tool '{tool_name}' failed: {result.error}"
            ),
        })

        if session.cancel_requested:
            break
    else:
        # Hit MAX_TOOL_ITERATIONS — return what we have
        full_response = "I reached the maximum number of tool calls. " + full_response

    return full_response
```

---

## System Prompt Update for Tool Use

When tools are registered, inject descriptions into SYSTEM_PROMPT:

```python
# In BaseAgent.run(), build messages as:
from app.tools.registry import tool_registry

tool_desc = tool_registry.tool_descriptions_for_prompt()
system_content = SYSTEM_PROMPT
if tool_registry.all_tools():
    system_content += f"\n\n{TOOL_USE_PROMPT_SUFFIX.format(tool_descriptions=tool_desc)}"

messages = [
    {"role": "system", "content": system_content},
    *session.history,
]
```

---

## Frontend: Tool Call Blocks

New component `ToolCallBlock.tsx`:
```tsx
// Renders inline when type="tool_call" or type="tool_result" WS event received
// Collapsed by default, expand on click
// tool_call: shows tool name + params in code block
// tool_result: shows success/failure + output preview (first 200 chars)
// Both styled with bg-slate-950 border border-slate-800 per DESIGN_SYSTEM.md
```

---

## Testing Pattern

```python
# Never use real Tavily/Playwright in unit tests

class _FakeSearchTool(BaseTool):
    name = "web_search"
    description = "fake"
    parameters_schema = {"query": "q"}

    async def execute(self, *, query: str = "", **_: str) -> ToolResult:
        return ToolResult(
            tool_name=self.name, success=True,
            output=f"Fake results for: {query}"
        )

# Test ReAct loop terminates at MAX_TOOL_ITERATIONS
async def test_react_loop_hard_cap():
    # Adapter always returns TOOL_CALL (infinite loop scenario)
    # Assert loop exits after MAX_TOOL_ITERATIONS, not infinite
    ...

# Test tool_call and tool_result WS events are sent
async def test_tool_events_streamed_to_hub():
    ...
```

---

## Common Pitfalls

- **Playwright not installed**: `playwright install chromium` required after
  `pip install playwright`. Add to setup docs. Fail gracefully if not installed.
- **Tavily key not set**: return helpful error, don't crash.
- **Infinite tool loop**: MAX_TOOL_ITERATIONS = 5 is the hard cap. Never skip it.
- **Tool results in session.history**: do NOT add tool_messages iterations to
  session.history — only the final human message and final assistant response.
  Tool call/result exchanges are ephemeral within the ReAct loop.
- **Mutating messages list**: always copy messages before ReAct loop,
  never mutate session.history directly during tool execution.
- **think=False**: apply to ALL adapter.stream() calls inside ReAct loop,
  same as everywhere else (ADR-012).
