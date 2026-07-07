# Archimedes — Architecture

> Version: 1.0.0 | Phase: MVP | Updated: 2026-06

## Vision

Self-hosted, multi-surface autonomous AI agent platform. Run AI agents that plan, execute, verify, and learn — locally or with cloud models — without proprietary infrastructure.

**Core principles:**
1. Local-first — fully offline with local models
2. Multi-surface — single backend, four frontends
3. Transparent — every agent action is logged and auditable
4. Secure — sandboxed execution, no accidental data leaks
5. Extensible — skill-based tool system, pluggable models

---

## Modules

### Core (app/core/)

| Component | File | Responsibility |
|-----------|------|----------------|
| App entry | app/main.py | FastAPI init, middleware, lifespan |
| Router | app/api/router.py | All HTTP endpoints |
| WebSocket Hub | app/core/ws_hub.py | Connection management, broadcasting |
| Session Manager | app/core/session.py | User sessions, isolation |
| Config | app/core/config.py | Pydantic settings from .env |
| Auth | app/core/auth.py | JWT + API key validation |

### Agent Engine (app/agents/)

| Component | File | Responsibility |
|-----------|------|----------------|
| Base Agent | app/agents/base.py | Abstract agent interface |
| Task Classifier | app/agents/classifier.py | Task complexity classification (SIMPLE/COMPLEX) via cheap LLM call |
| MCTS Planner | app/agents/mcts.py | UCB1 tree search, task decomposition |
| MoA | app/agents/moa.py | Multi-model ensemble + CoT aggregation |
| HydraSwarm | app/agents/hydra.py | Parallel agent pool |
| CodeAct | app/agents/codeact.py | Python sandbox execution |
| Router | app/agents/router.py | Model selection by task complexity |
| Verifier | app/agents/verify.py | Output validation |

### Tools (app/tools/)

| Tool | File | Description |
|------|------|-------------|
| Bash | app/tools/bash.py | Sandboxed terminal execution |
| FileSystem | app/tools/filesystem.py | Read/write with path validation |
| Web Search | app/tools/search.py | Web search via API |
| Browser | app/tools/browser.py | Playwright browser agent |
| Git | app/tools/git.py | Repository operations |
| Memory | app/tools/memory.py | ChromaDB read/write |

### Memory (app/memory/)

| Component | File | Description |
|-----------|------|-------------|
| Vector Store | app/memory/chroma.py | Semantic search via ChromaDB |
| State Store | app/memory/sqlite.py | Structured state in SQLite |
| Blackboard | app/memory/blackboard.py | Shared agent context |
| Skill Library | app/memory/skills.py | Reusable task patterns |

### Models (app/models/)

| Adapter | File | Provider |
|---------|------|----------|
| Local | app/models/local.py | Qwen 3 27B via Ollama |
| OpenAI | app/models/openai.py | GPT-4o, o1 |
| Anthropic | app/models/anthropic.py | Claude Sonnet/Opus |
| Google | app/models/google.py | Gemini 2.0 Flash |

---

## Data Flow

### Request Flow

```
User input (any surface)
  -> WebSocket / HTTP endpoint
  -> Auth middleware (JWT/API key)
  -> Session Manager (create/restore)
  -> classify_task()
      -> SIMPLE: BaseAgent (direct stream)
      -> COMPLEX: MCTSPlanner -> verify -> BaseAgent (plan-injected stream)
  -> Memory: persist result, update ChromaDB
  -> Audit Trail: log all actions
  -> Stream response via WebSocket
```

### WebSocket Protocol

Client to Server:
```json
{ "type": "task", "session_id": "uuid", "payload": { "message": "string" } }
```

Server to Client (streaming):
```json
{ "type": "stream", "payload": { "delta": "string" } }
{ "type": "tool_call", "payload": { "tool": "bash", "input": {} } }
{ "type": "tool_result", "payload": { "output": "string" } }
{ "type": "done", "payload": { "usage": {} } }
{ "type": "error", "payload": { "message": "string" } }
```

---

## Technology Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Backend | FastAPI | Async-first, native WebSocket, auto OpenAPI |
| Vector DB | ChromaDB | Local-first, zero infra |
| Relational | SQLite + aiosqlite | Zero infra for MVP |
| Desktop | Tauri v2 | ~10MB bundle, Rust security model |
| Mobile | Capacitor | Shared web code, native API access |
| Web | Next.js | SSR + App Router, TypeScript native |
| Local LLM | Qwen 3 27B | Best quality/VRAM ratio |
| Styling | Tailwind + Radix UI | Utility-first, accessible primitives |

See docs/DECISIONS.md for full ADRs.

---

## Directory Structure

```
archimedes/
├── app/                    # FastAPI backend
│   ├── main.py
│   ├── api/
│   ├── agents/
│   ├── core/
│   ├── memory/
│   ├── models/
│   └── tools/
├── web/                    # Next.js web app
├── desktop/                # Tauri v2 desktop
├── mobile/                 # Capacitor mobile
├── cli/                    # Python CLI
├── docs/                   # Documentation
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
└── .agents/skills/
```
