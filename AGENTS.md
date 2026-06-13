# Archimedes — Agent Instructions

> This file is automatically prepended to every prompt by Antigravity.
> Read it entirely before executing anything.

---

## Project Stack

- **Backend:** FastAPI + WebSocket + Python 3.11+
- **Web:** Next.js 15 + React 18 + TypeScript + Tailwind CSS
- **Desktop:** Tauri v2 (Rust + TypeScript)
- **Mobile:** Capacitor 6 (TypeScript)
- **Local LLM:** Qwen 3 27B via Ollama
- **Vector DB:** ChromaDB
- **State:** SQLite + aiosqlite

---

## Safety Rules (check before every action)

- Never access files outside the current workspace
- Never modify `.env`, `*.key`, `*.pem`, `secrets/`
- If the action is destructive or irreversible — ask for confirmation first
- Never commit credentials or API keys
- If unsure about scope — pause and ask

---

## Code Standards

### Python
- PEP 8 compliance required
- Type hints on every function and method — no bare `Any`
- Public functions and classes require docstrings
- All config via `app/core/config.py` — no hardcoded values
- HTTP client: `httpx` (not `requests`)
- Async: `asyncio` + `anyio`

### TypeScript
- Strict mode required (`"strict": true` in tsconfig)
- No `any` type — use `unknown` and narrow
- Explicit return types on all exported functions
- UI state: Zustand; server state: React Query

---

## Architecture Rules

- Read `docs/ARCHITECTURE.md` before modifying any module
- Follow existing patterns — don't invent new ones without discussion
- Module boundaries: agents don't import from core, tools don't import from agents
- All user input must be validated before reaching business logic

---

## Security Rules

- No credentials in source code. Ever.
- All filesystem operations go through `validate_path()`
- All LLM inputs go through prompt injection detection
- Rate limiting applied at session and IP level

---

## Git Rules

- Branch naming: `feature/kebab-name` | `bugfix/id-name` | `refactor/scope-what`
- Conventional commits required:
  - `feat(scope): description`
  - `fix(scope): description`
  - `docs(scope): description`
  - `refactor(scope): description`
  - `test(scope): description`
  - `chore(scope): description`
- One commit = one atomic task
- Tests must pass before opening PR

---

## Done Criteria

A task is complete when:
1. Code compiles without errors
2. All existing tests still pass
3. New tests written and passing
4. `mypy --strict` / `tsc --noEmit` passes with no new errors
5. PR opened with conventional commit title
6. No secrets or debug code in commit

---

## Forbidden

```
NEVER:
- rm -rf (any path)
- Modify node_modules/ or vendor/
- Commit .env files
- Add hardcoded API keys or passwords
- Skip writing tests
- Modify files outside current task scope
- Use requests library (use httpx)
- Use any type in TypeScript
```

---

## Context Files

Before touching any module, read:
- `docs/ARCHITECTURE.md` — system design and module boundaries
- `docs/ROADMAP.md` — current phase and priorities
- `docs/DESIGN_SYSTEM.md` — UI standards (frontend tasks)
- `docs/SECURITY.md` — security constraints (auth/tool tasks)
- `docs/DECISIONS.md` — why we made key architectural choices
