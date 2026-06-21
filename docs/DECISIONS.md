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

---

## ADR-009: Static export for Next.js in Phase 1

**Date:** 2026-06 | **Status:** Accepted | **Superseded by:** ADR-010 (Phase 2)

**Context:** Capacitor requires `webDir:'out'` (static files). Tauri requires `frontendDist:'../out'`. Both depend on `next build` producing a static `out/` directory rather than the default `.next/` server output.

**Decision:** `output: 'export'` in `web/next.config.js` for Phase 1 only.

**Consequences:**
- API routes (`app/api/`) disabled — all API calls go directly to FastAPI backend
- Server Components with data fetching disabled
- `images.unoptimized: true` required (no Image Optimization server)

**Reversal plan:** Remove `output: 'export'` in Phase 2 when `app/api/` proxy routes to FastAPI are added. See `TODO(phase-2)` comment in `web/next.config.js`.

---

## ADR-010: Anonymous JWT issuance for Phase 1

**Date:** 2026-06 | **Status:** Accepted | **Must be revisited:** Phase 6 (Security)

**Context:** WebSocket requires a JWT, but Phase 1 has no user registration/login system yet.

**Decision:** `POST /auth/token` issues an anonymous JWT to any caller, rate-limited to 5 requests/minute/IP as a basic abuse guard.

**Consequences:**
- Anyone with network access to the backend can obtain a valid session token.
- This is acceptable ONLY for local development (backend bound to `localhost`).
- This MUST be replaced before any public deployment.

**Reversal plan:** Phase 6 replaces this with real user accounts (registration/login) and removes anonymous token issuance entirely.

---

## ADR-011: CPU-based embedding for memory (not Ollama)

**Date:** 2026-06 | **Status:** Accepted

**Context:** Phase 2 needs an embedding model for ChromaDB semantic search. The local LLM (qwen3:14b) already consumes ~9GB of the 12GB available VRAM on the RTX 3060.

**Decision:** Use ChromaDB's built-in default embedding function (ONNX-based MiniLM-L6-v2, runs on CPU via onnxruntime) rather than an Ollama-served embedding model.

**Reasons:**
- Zero VRAM contention with qwen3:14b — embedding runs entirely on CPU
- Avoids Ollama model-swap latency: serving two models (chat + embedding) on demand causes Ollama to load/unload models between requests, adding latency to every chat turn
- Sufficient retrieval quality for short chat-message embeddings at our current scale
- No additional `ollama pull` step required for setup

**Consequences:**
- Embedding quality is lower than a dedicated embedding model (e.g., nomic-embed-text, mxbai-embed-large)
- CPU embedding is slower in absolute terms, but the volume (single chat messages, not bulk documents) makes this a non-issue in practice

**Reversal plan:** If recall quality proves insufficient, revisit when a second GPU is available (see hardware upgrade path in `.env.example`) — at that point a dedicated embedding model can run without contending with the chat model.

**Alternatives rejected:**
- Ollama `nomic-embed-text`: VRAM contention with qwen3:14b, model-swap latency per turn
- OpenAI/cloud embedding API: breaks local-first principle, adds cost and network dependency

---

## ADR-012: Disable Ollama thinking mode across all call sites

**Date:** 2026-06 | **Status:** Accepted | **Should be revisited:** if/when a "show reasoning" UI feature is deliberately built

**Context:**
qwen3:14b defaults to thinking mode when the `think` field is omitted from Ollama API requests. Reasoning tokens and content tokens share the same `num_predict` budget. Direct testing against our Ollama 0.30.10 + qwen3:14b confirmed: with `max_tokens=10` (classifier, MCTS `_simulate`), 100% of budget was consumed by thinking, leaving `message.content` completely empty every time. With `max_tokens=2048` (main chat), ~88% of budget went to thinking in a representative test, truncating the visible response mid-sentence (`done_reason: "length"`).

**Decision:**
Explicitly set `think=false` (top-level field, not nested in options) on every `adapter.stream()` call site in the codebase.

**Consequences:**
- Faster responses across the board (eliminates the 7-8x latency inflation observed).
- No more silent mid-sentence truncation.
- The model's reasoning process is not used at all — answer quality for genuinely complex questions may be lower than a properly-surfaced thinking-mode implementation could provide.

**Reversal plan:**
If reasoning quality becomes a priority, build a dedicated "show reasoning" feature — separate WS event type for `message.thinking`, collapsed-by-default UI panel, and a content-specific token budget (e.g., reserve `num_predict` headroom for content specifically, or query thinking and content as genuinely separate generation passes) rather than re-enabling thinking blindly into the existing shared-budget setup.

