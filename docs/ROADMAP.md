# Archimedes — Roadmap

> Legend: Not started | In progress | Done

---

## Phase 1: MVP Core (2 weeks)

**Goal:** Working end-to-end pipeline. One agent, one tool, real UI.

### Backend
- [ ] FastAPI app setup with lifespan hooks
- [ ] WebSocket hub (connection management, broadcasting)
- [ ] Session manager (create/restore/delete)
- [ ] JWT + API key auth middleware
- [ ] Config via Pydantic Settings from .env
- [ ] Base agent class with abstract interface
- [ ] Single model adapter (Qwen 3 via Ollama)
- [ ] Bash tool (sandboxed subprocess)
- [ ] Filesystem tool (path validation)
- [ ] Token-by-token streaming via WebSocket
- [ ] Audit trail (SQLite log)

### Web UI (Next.js)
- [ ] Chat interface with streaming display
- [ ] WebSocket client hook
- [ ] Message history with tool call visualization
- [ ] Loading states and error handling
- [ ] Session management UI

### Infrastructure
- [ ] Docker Compose for local dev
- [ ] pytest suite with >70% coverage on core
- [ ] mypy strict mode passing
- [ ] CI: pytest + mypy on every push

**Done criteria:** User sends message → agent executes bash → result streams back → shown in UI.

---

## Phase 2: Smart Memory (1 week)

**Goal:** Agent remembers context across sessions.

- [ ] ChromaDB integration and embedding pipeline
- [ ] Semantic search on past sessions
- [ ] Memory injection into agent context window
- [ ] Cross-session recall tests
- [ ] Memory management UI (view/delete entries)

**Done criteria:** Agent references information from a previous session without being told.

---

## Phase 3: MCTS Planner (2 weeks)

**Goal:** Agent decomposes complex tasks and plans before executing.

- [ ] MCTS with UCB1 implementation
- [ ] Task decomposition prompt template
- [ ] Step-by-step execution with rollback on failure
- [ ] Self-Verification Engine (output validation)
- [ ] Retry logic on failed steps (max 3 retries)
- [ ] Plan visualization in UI
- [ ] MCTS unit + integration tests

**Done criteria:** "Build a REST API with auth" → agent produces verified working result in planned steps.

---

## Phase 4: HydraSwarm (2 weeks)

**Goal:** Parallel agent execution for independent subtasks.

- [ ] HydraSwarm coordinator
- [ ] Async worker agent pool
- [ ] Shared Blackboard for inter-agent context
- [ ] Task dependency graph (topological sort)
- [ ] Conflict resolution for concurrent file writes
- [ ] Progress monitoring in UI
- [ ] Load balancing across workers

**Done criteria:** 3 independent subtasks complete 3x faster than sequential execution.

---

## Phase 5: Mixture of Agents (1 week)

**Goal:** Ensemble of models produces higher quality output than any single model.

- [ ] MoA coordinator
- [ ] Multi-model adapter (OpenAI, Anthropic, Google, local)
- [ ] Chain-of-Thought aggregation
- [ ] Voting and consensus mechanism
- [ ] Cost vs quality routing logic
- [ ] MoA comparison view in UI

**Done criteria:** Code generation: MoA output passes more tests than single-model output on same prompt.

---

## Phase 6: Security and Sandbox (2 weeks)

**Goal:** Production-grade security. No escape from sandbox.

- [ ] MicroVM isolation for code execution (gVisor or Firecracker)
- [ ] 33-pattern prompt injection detection pipeline
- [ ] Shared rate limiter (per session + per IP)
- [ ] Input sanitization before any LLM call
- [ ] Security audit log (separate from main audit trail)
- [ ] CORS and CSP hardening
- [ ] Pre-commit hook: secrets scanner
- [ ] OWASP Top 10 checklist pass

**Done criteria:** Prompt injection test suite passes. Code execution cannot access host filesystem.

---

## Phase 7: Production Ready (2 weeks)

**Goal:** Deployable, scalable, polished on all four surfaces.

- [ ] Desktop (Tauri v2): Windows, macOS, Linux signed builds
- [ ] Mobile (Capacitor): Android + iOS builds
- [ ] CLI: install script + pip package
- [ ] PostgreSQL migration path from SQLite
- [ ] Redis pub/sub for horizontal WS scaling
- [ ] Monitoring: Prometheus + Grafana dashboards
- [ ] One-click Docker deploy script
- [ ] Full documentation pass
- [ ] Performance target: first token < 100ms

**Done criteria:** All 4 surfaces work. Fresh deploy completes in under 5 minutes.

---

## Future (Post-MVP)

- Model Council: multi-model consensus voting on critical decisions
- Proactive Triggers: event-based autonomous agent activation
- Deep Research mode: autonomous multi-source synthesis to slides
- Plugin marketplace for community tools
- Team and multi-user support
- Enterprise: SSO, audit compliance, data residency controls
