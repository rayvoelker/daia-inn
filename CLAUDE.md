# daia-inn

MCP server exposing the daia workstation's AI infrastructure. The medieval inn — tasks go in, PRs come out.

## System

- Workstation: daia-ts, x86_64, 32 cores, 124GB RAM
- GPU: NVIDIA RTX 4090 (24GB VRAM)
- Container runtime: Docker with nvidia runtime
- Python: 3.10 (uv managed)
- Network: Tailscale (daia.tailnet)
- Ollama: Docker container, port 11434

## Commands

- `docker compose up -d` — start Ollama + inn
- `docker compose down` — stop everything
- `docker compose logs inn` — view inn logs
- `uv run python -m src.server` — run inn locally (dev mode)

## Architecture

daia-inn is a Python MCP server running alongside Ollama in docker-compose. It exposes resources (windows into the inn) and tools (actions) over the MCP protocol. Accessible locally and over Tailscale.

### Oven Abstraction

Ollama is the current "oven" (model serving backend), but the architecture treats it as a swappable plugin. The key separation:

- **Parsers** (`health.py`, `system.py`) work on raw dicts and strings — no Ollama-specific imports
- **I/O clients** (`ollama.py`) fetch data and return dicts — this is the only Ollama-coupled layer
- **Server** (`server.py`) composes them — doesn't know how data was fetched

To swap backends (vLLM, llama.cpp, TGI, etc.), replace `ollama.py` with a new client returning the same dict shapes. Parsers and server don't change. Keep this boundary clean as the inn grows.

### Current Roster (v0.1)

| Role | Model | Location | Speed |
|------|-------|----------|-------|
| Line Cook | gemma4:26b | GPU | 50 tok/s |
| Scout | gemma4:e4b-cpu | CPU/RAM | 13 tok/s |

### MCP Resources

- `inn://health` — model status, GPU/RAM usage, Ollama health

## Key Docs

- `docs/daia-inn-v01-design.md` — v0.1 design spec
- `docs/design-the-inn-model.md` — the inn model (role taxonomy, economics, adaptive routing)
- `docs/superpowers/specs/2026-04-04-new-roles-design.md` — Bard, Farmer, Carter, Scribe design spec
- `docs/blog-the-watchman-ships.md` — v0.1 ship log (latest)
- `docs/blog-claude-code-agents.md` — how the pipeline works
- `docs/blog-the-inn-model.md` — public-facing writeup

## Safety Rules

- Never expose secrets, credentials, or PII through MCP resources
- Tailscale provides network-level access control — no app-level auth in v0.1
- MCP resources are read-only in v0.1 — no tools that modify state
