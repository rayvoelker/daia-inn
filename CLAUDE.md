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
- `docs/blog-claude-code-agents.md` — how the pipeline works
- `docs/blog-the-inn-model.md` — public-facing writeup

## Safety Rules

- Never expose secrets, credentials, or PII through MCP resources
- Tailscale provides network-level access control — no app-level auth in v0.1
- MCP resources are read-only in v0.1 — no tools that modify state
