# Archimedes — Architecture Decision Records

> Format: ADR (Architecture Decision Record)
> Status options: Proposed | Accepted | Deprecated | Superseded

---

## ADR-001: FastAPI as backend framework

**Date:** 2026-05 | **Status:** Accepted

**Context:** Need async-first HTTP + WebSocket server in Python with good developer experience.

**Decision:** FastAPI + uvicorn.

**Reasons:**
- Native async/await — critical for streaming agent output token by token
- WebSocket support built in
- Auto-generated OpenAPI documentation
- Pydantic integration for request validation
- Fastest Python HTTP framework (ASGI/uvicorn)

**Alternatives rejected:**
- Django: sync-first, WebSocket requires Django Channels (complexity)
- Flask: no native async, no WebSocket
- aiohttp: lower-level, worse DX

---

## ADR-002: ChromaDB for vector storage

**Date:** 2026-05 | **Status:** Accepted

**Context:** Need persistent vector store for agent memory across sessions.

**Decision:** ChromaDB in local embedded mode.

**Reasons:**
- Local-first: no cloud dependency, zero config
- Python-native client
- Good performance for single-user workload
- Easy migration to server mode when scaling

**Alternatives rejected:**
- Pinecone: cloud-only, external dependency
- Weaviate: heavier infra footprint
- pgvector: requires PostgreSQL (overkill at MVP)
- FAISS: no persistence, limited metadata search

---

## ADR-003: Tauri v2 for desktop

**Date:** 2026-05 | **Status:** Accepted

**Context:** Need cross-platform desktop app (Windows, macOS, Linux).

**Decision:** Tauri v2 (Rust + system webview).

**Reasons:**
- ~10MB bundle vs ~150MB Electron
- Rust security model: no Node.js process in production binary
- Uses OS browser engine — no bundled Chromium
- Strong IPC model for native calls

**Alternatives rejected:**
- Electron: large bundle, Node.js attack surface
- Flutter: Dart ecosystem, separate component library
- Native per-platform: too slow, no shared web code

---

## ADR-004: Capacitor for mobile

**Date:** 2026-05 | **Status:** Accepted

**Context:** Need mobile app (Android + iOS) sharing the web codebase.

**Decision:** Capacitor.

**Reasons:**
- Shares React components with the web app entirely
- Simpler than React Native (no bridge)
- Native API access via plugins
- Community plugins cover all core needs (haptics, keyboard, status bar)

**Alternatives rejected:**
- React Native: separate component library, Metro bundler, bridge latency
- Flutter: Dart, no code sharing with web
- PWA only: limited native API access, not on app stores

---

## ADR-005: SQLite for state storage (MVP)

**Date:** 2026-05 | **Status:** Accepted | **Superseded by ADR-006 at Phase 7**

**Context:** Need relational storage for sessions, users, audit logs at MVP.

**Decision:** SQLite + aiosqlite.

**Reasons:**
- Zero infrastructure: file-based, no server
- Sufficient for single-user MVP load
- SQLAlchemy abstracts the dialect — easy PostgreSQL migration
- aiosqlite: async wrapper, no blocking

**Migration path:** Swap SQLAlchemy dialect string to PostgreSQL at Phase 7.

---

## ADR-006: Local model via Ollama

**Date:** 2026-05 | **Status:** Accepted

**Context:** Need local LLM inference for privacy, cost, and offline capability.

**Decision:** Qwen 3 27B via Ollama (OpenAI-compatible API).

**Reasons:**
- Best quality/VRAM ratio for RTX 3060 12GB (current) and RTX 3090 24GB (target)
- Ollama provides OpenAI-compatible API — trivial adapter
- Strong coding, reasoning, and multilingual capability
- Fully offline capable

**Alternatives rejected:**
- Llama 3.1 70B: requires 48GB+ VRAM at full precision
- Mistral: weaker on code benchmarks
- API-only (GPT-4o): cost per token, privacy concerns, no offline

---

## ADR-007: Conventional Commits + feature branches

**Date:** 2026-05 | **Status:** Accepted

**Context:** Solo developer project that will have AI agents committing code.

**Decision:** Conventional Commits format + feature/* branches + PR to main.

**Commit format:**
```
feat(scope): description
fix(scope): description
docs(scope): description
refactor(scope): description
test(scope): description
chore(scope): description
```

**Branch naming:**
```
feature/kebab-description
bugfix/issue-id-description
refactor/scope-description
```

**Reasons:**
- Machine-readable history (AI agents can follow the format)
- Enables automated changelog generation
- Clear scope for every change
- PR-based flow works with GitHub MCP for AI code review

---

## ADR-008: Tailwind CSS + Radix UI for UI

**Date:** 2026-05 | **Status:** Accepted

**Context:** Need a UI system that works across web, desktop (Tauri), and mobile (Capacitor).

**Decision:** Tailwind CSS + Radix UI primitives.

**Reasons:**
- Tailwind: utility-first, no class-name collisions, consistent design tokens
- Radix UI: unstyled, accessible primitives — full control over visual style
- Both work in any React environment (Next.js, Tauri webview, Capacitor)
- Framer Motion for transitions where needed (used sparingly)

**Alternatives rejected:**
- shadcn/ui: good but opinionated styles that conflict with our dark design
- Material UI: too opinionated, large bundle
- Chakra UI: runtime CSS-in-JS, worse performance
