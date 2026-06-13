# Skill: Testing

## Trigger
Use when asked to "write tests", "add tests", "test coverage", or "regression test".

---

## Frameworks

| Language | Framework | Config |
|----------|-----------|--------|
| Python | pytest + pytest-asyncio + pytest-cov | `pytest.ini` |
| TypeScript | vitest + @testing-library/react | `vitest.config.ts` |
| E2E | playwright | `playwright.config.ts` |

---

## File Locations

```
tests/unit/test_[module].py              # Python unit tests
tests/integration/test_[module].py       # Python integration tests
web/components/__tests__/[Comp].test.tsx # React component tests
tests/e2e/[feature].spec.ts             # E2E tests
```

---

## Coverage Targets

- Unit: >80% per module
- Integration: all API endpoints covered
- E2E: critical user flows covered (chat, session, tool execution)

---

## Python Test Patterns

### Naming
```python
# Format: test_[function]_[scenario]_[expected_result]
def test_validate_path_outside_workspace_raises_security_error():
    ...

def test_agent_run_with_valid_task_returns_output():
    ...
```

### Async Tests
```python
@pytest.mark.asyncio
async def test_websocket_receives_stream():
    async with AsyncClient(app=app, base_url="http://test") as client:
        async with client.websocket_connect("/ws/test-session") as ws:
            await ws.send_json({"type": "task", "payload": {"message": "hello"}})
            data = await ws.receive_json()
            assert data["type"] in ["stream", "done"]
```

### Mocking Rules
```python
# Mock external calls only (LLM APIs, HTTP requests)
# Never mock internal business logic

@patch("app.models.openai.AsyncOpenAI")
async def test_agent_calls_model(mock_openai):
    mock_openai.return_value.chat.completions.create = AsyncMock(
        return_value=build_mock_response("test output")
    )
    result = await agent.run("task")
    assert result.output == "test output"
```

---

## React Test Patterns

```typescript
// Test what the user sees, not implementation details
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

test("sends message on Enter key", async () => {
  const mockSend = vi.fn();
  render(<ChatInput onSend={mockSend} />);
  
  const input = screen.getByRole("textbox");
  await userEvent.type(input, "hello{Enter}");
  
  expect(mockSend).toHaveBeenCalledWith("hello");
  expect(input).toHaveValue("");
});
```

---

## Rules

- Clean up state between tests — use fixtures with teardown
- Don't test external services in unit tests — mock them
- Use factories for test data, not hardcoded values
- Each test has one clear assertion purpose
- Test file mirrors source file structure

---

## Output After Writing Tests

1. List all test files created/modified
2. Run coverage: `pytest --cov=app tests/unit/ --cov-report=term-missing`
3. Flag any code paths with <80% coverage
4. Suggest additional edge cases if needed
