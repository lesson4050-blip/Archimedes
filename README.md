# Archimedes

> Autonomous AI agent platform. Multi-surface. Self-hosted.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.11+-green.svg)
![TypeScript](https://img.shields.io/badge/typescript-5.0+-blue.svg)
![Status](https://img.shields.io/badge/status-MVP-orange.svg)

## What Is Archimedes

Archimedes is an open-source autonomous AI agent platform. Runs local models (Qwen 3 27B) and cloud LLMs through a unified interface across four surfaces: CLI, Desktop, Mobile, and Web.

Built for developers who want full control over their AI agent infrastructure without proprietary dependencies.

## Key Features

- **Autonomous agent execution** — MCTS planning, tool calling, self-verification
- **Persistent memory** — ChromaDB vector store, cross-session recall
- **Multi-agent orchestration** — HydraSwarm parallel agents, Mixture of Agents
- **Multi-surface** — CLI, Tauri v2 desktop, Capacitor mobile, Next.js web
- **Real-time streaming** — WebSocket output with full audit trail
- **Secure sandbox** — code execution isolation, 33-pattern prompt injection defense

## Architecture

```
Client Layer: CLI | Desktop (Tauri v2) | Mobile (Capacitor) | Web (Next.js)
                           │
                    WebSocket / HTTP
                           │
              ┌────────────▼────────────┐
              │      FastAPI Core       │
              │  Auth │ WS │ Router     │
              └────────────┬────────────┘
                           │
              ┌────────────▼────────────┐
              │     Agent Engine        │
              │  MCTS │ MoA │ Hydra     │
              └────────────┬────────────┘
                           │
              ┌────────────▼────────────┐
              │   Memory & Tools        │
              │  ChromaDB │ SQLite      │
              └─────────────────────────┘
```

## Quick Start

### Backend

```bash
git clone https://github.com/lesson4050-blip/archimedes
cd archimedes
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Web UI

```bash
cd web && npm install && npm run dev
```

### Desktop (Tauri v2)

```bash
cd desktop && npm install && npm run tauri dev
```

## Documentation

| Doc | Description |
|-----|-------------|
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design, modules, data flow |
| [ROADMAP.md](docs/ROADMAP.md) | Phase-by-phase development plan |
| [DESIGN_SYSTEM.md](docs/DESIGN_SYSTEM.md) | Colors, typography, components |
| [PLATFORM_SUPPORT.md](docs/PLATFORM_SUPPORT.md) | Desktop/mobile/web matrix |
| [SECURITY.md](docs/SECURITY.md) | Threat model, auth, sandboxing |
| [DECISIONS.md](docs/DECISIONS.md) | Architectural decision records |

## Contributing

1. Fork the repo
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit with conventional commits: `feat(scope): description`
4. Open a PR — CI must pass before merge

## License

MIT — see [LICENSE](LICENSE)
