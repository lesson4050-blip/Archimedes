# Archimedes — Agent Instructions

> This file is automatically prepended to every prompt by Antigravity.
> Read it entirely before executing anything.

---

## Project Stack

- **Backend:** FastAPI + WebSocket + Python 3.11+
- **Web:** Next.js 15 + React 18 + TypeScript + Tailwind CSS
- **Desktop:** Tauri v2 (Rust + TypeScript)
- **Mobile:** Capacitor 6 (TypeScript)
- **Local LLM:** Qwen3:14B Q4_K_M via Ollama (fits RTX 3060 12GB)
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

## UI Rules

### Theme
- Dark mode is the default (`bg-slate-900` background)
- Light mode must be available via theme toggle
- Use `next-themes` for theme management
- Never hardcode colors — use Tailwind classes that respect dark: prefix
- All components must look correct in BOTH dark and light modes

### No Stub Buttons — CRITICAL
- EVERY button, link, and interactive element must have a real handler
- If the feature is not implemented yet — DO NOT render the button at all
- NEVER use: `onClick={() => {}}`, `onClick={console.log}`, `href="#"`, `disabled` as a placeholder
- "Coming soon" UI is forbidden
- If a button's feature is out of scope for the current task — omit the button entirely
- A missing button is always better than a non-functional one

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

## Remote Verification Protocol

This section is MANDATORY. Skipping it is a violation of AGENTS.md.

### After ANY git push or PR update:

Run these commands in order and include their output in your summary:

```bash
# 1. Confirm commits reached remote
git log --oneline origin/<branch-name> -5

# 2. Confirm PR reflects the changes
gh pr view <PR-number> --json files,commits,state | jq '.commits[-3:]'
```

If either command fails or shows stale data — the task is NOT done.
Do not write "successfully pushed" until both commands confirm it.

### After ANY claim of "task complete":

Before reporting to the user, self-check:
- Did I run git push AND verify with git log origin/<branch>?
- Does the GitHub PR show new commits with updated SHAs?
- If I only ran commands locally without pushing — the task is NOT complete.

### Forbidden phrases until remote is verified:

NEVER say these until git log origin/<branch> confirms the push:
- "Successfully pushed"
- "PR has been updated"
- "All changes are live"
- "Task complete"

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
- Render stub/placeholder buttons (if feature not ready — omit the button)
- Hardcode theme colors (use Tailwind dark: classes)
```

---

## Context Files

Before touching any module, read:
- `docs/ARCHITECTURE.md` — system design and module boundaries
- `docs/ROADMAP.md` — current phase and priorities
- `docs/DESIGN_SYSTEM.md` — UI standards (frontend tasks)
- `docs/SECURITY.md` — security constraints (auth/tool tasks)
- `docs/DECISIONS.md` — why we made key architectural choices
