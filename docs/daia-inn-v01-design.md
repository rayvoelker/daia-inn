# daia-inn v0.1 — Design Spec

> Spec date: 2026-04-03. Status: approved design, pending implementation.

## 1. What Is daia-inn?

daia-inn is a Python MCP server that exposes the daia workstation's AI infrastructure as observable, queryable resources. It runs in docker-compose alongside Ollama and is accessible over Tailscale from any MCP client.

The metaphor: daia is a medieval inn. Tasks (customers) walk in, get classified, routed to the right agent (cook), and come out as accepted PRs (satisfied customers). daia-inn is the **building itself** — the front door, the windows to peer in, and eventually the kitchen orchestration.

### The Inn Serves Any Repo

daia-inn is NOT specific to munews.app. It's workstation infrastructure. Any project on daia (or reachable from daia) can be a customer of the inn.

### The mu Principle

v0.1 is the smallest possible thing: one MCP resource, one docker service, one window to peer through. Everything else is future work.

## 2. v0.1 Scope: "The Watchman"

The watchman's one job: look through the window and report what he sees.

### What Ships

- Python MCP server using the `mcp` SDK
- One MCP resource: `inn://health` — model status, GPU/RAM usage, Ollama health
- Runs as a Docker service in docker-compose alongside Ollama
- Listens on a configurable port (default: `3001`)
- Accessible over Tailscale from any MCP client

### What Does NOT Ship

- Task submission / queue (no front door yet — just windows)
- The ledger (no stats collection)
- Agent dispatch (no kitchen — orchestrator stays on host)
- GitHub Issue integration (no external customers)
- Any agent roles (innkeeper, cook, etc. remain as Claude Code agents on host)
- Authentication (Tailscale handles network-level access)

### Success Criteria

From a Claude Code session on another machine:

```
> What models are loaded on daia?

gemma4:26b          GPU      23.1 GB    (line cook, ready)
gemma4:e4b-cpu      CPU/RAM  11.9 GB    (scout, ready)

GPU:  [████████████████████░] 23.1 / 24.0 GB (96%)
RAM:  [██████░░░░░░░░░░░░░░] 38 / 124 GB (31%)
Ollama: running (v0.20.0)
```

That's it. That's v0.1.

## 3. Architecture

```
┌──────────────────────────────────────────────┐
│                    daia                        │
│                                                │
│  docker-compose                                │
│  ┌──────────────┐  ┌───────────────────────┐  │
│  │   ollama      │  │   daia-inn (MCP)      │  │
│  │   :11434      │  │   :3001               │  │
│  │               │  │                       │  │
│  │  gemma4:26b   │  │  Resources:           │  │
│  │  gemma4:e4b   │  │    inn://health       │  │
│  │               │  │                       │  │
│  │  GPU: RTX 4090│  │  Reads from:          │  │
│  └──────────────┘  │    - Ollama API        │  │
│                     │    - nvidia-smi        │  │
│                     │    - /proc/meminfo     │  │
│                     └───────────────────────┘  │
│                                                │
│  Tailscale: daia.tailnet ──────────────────────┤
│                                                │
│  Host:                                         │
│    claude --agent orchestrator (unchanged)      │
│    .claude/agents/ (unchanged)                  │
└────────────────────────────────────────────────┘
         │
         │ Tailscale
         ▼
┌─────────────────┐
│  Your laptop    │
│  Claude Code    │
│  MCP client     │
│  connects to    │
│  daia:3001      │
└─────────────────┘
```

### Data Flow

```
MCP Client (laptop)
  → connects to daia:3001 over Tailscale
  → requests resource: inn://health
  → daia-inn queries:
      1. Ollama API (http://ollama:11434/api/ps) → loaded models
      2. Ollama API (http://ollama:11434/api/version) → version
      3. nvidia-smi → GPU VRAM usage
      4. /proc/meminfo → system RAM
  → returns formatted health report
```

## 4. Tech Stack

- **Python 3.10+** (matches daia's existing Python)
- **`mcp` SDK** — Anthropic's official MCP Python library
- **Docker** — runs alongside Ollama in existing docker-compose
- **No database** — v0.1 has no persistent state
- **No auth** — Tailscale provides network-level security

### Dependencies (minimal)

```
mcp
httpx          # async HTTP client for Ollama API
```

## 5. MCP Resource: `inn://health`

### Response Shape

```json
{
  "ollama": {
    "status": "running",
    "version": "0.20.0",
    "url": "http://ollama:11434"
  },
  "models": [
    {
      "name": "gemma4:26b",
      "role": "line_cook",
      "location": "GPU",
      "size_gb": 23.1,
      "status": "loaded"
    },
    {
      "name": "gemma4:e4b-cpu",
      "role": "scout",
      "location": "CPU/RAM",
      "size_gb": 11.9,
      "status": "loaded"
    }
  ],
  "gpu": {
    "name": "NVIDIA RTX 4090",
    "vram_used_gb": 23.1,
    "vram_total_gb": 24.0,
    "utilization_pct": 96
  },
  "system": {
    "ram_used_gb": 38,
    "ram_total_gb": 124,
    "utilization_pct": 31
  }
}
```

### Role Mapping

The health resource maps model names to inn roles so clients understand what each model does:

```python
ROLE_MAP = {
    "gemma4:26b": "line_cook",
    "gemma4:e4b-cpu": "scout",
    "gemma4:e4b": "scout_gpu",
    "gemma4:31b": "head_chef",
}
```

This is configurable — different inns (workstations) have different rosters.

## 6. Docker Integration

### docker-compose.yml (additions to existing)

```yaml
services:
  ollama:
    # ... existing Ollama config unchanged ...

  inn:
    build: .
    ports:
      - "3001:3001"
    environment:
      - OLLAMA_HOST=http://ollama:11434
      - INN_PORT=3001
    depends_on:
      - ollama
    # GPU stats require access to nvidia-smi
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [utility]  # nvidia-smi only, not full GPU
    volumes:
      - /proc/meminfo:/host/meminfo:ro
    restart: unless-stopped
```

### Dockerfile

```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ ./src/
CMD ["python", "-m", "src.server"]
```

## 7. MCP Client Configuration

### On daia (local)

```json
// .claude/settings.local.json or project .mcp.json
{
  "mcpServers": {
    "daia-inn": {
      "command": "docker",
      "args": ["exec", "-i", "daia-inn-inn-1", "python", "-m", "src.server", "--stdio"]
    }
  }
}
```

### On laptop (remote over Tailscale)

```json
{
  "mcpServers": {
    "daia-inn": {
      "type": "sse",
      "url": "http://daia:3001/sse"
    }
  }
}
```

## 8. File Structure

```
daia-inn/
├── docker-compose.yml          # Ollama + inn
├── Dockerfile                  # inn service
├── requirements.txt            # mcp, httpx
├── src/
│   ├── __init__.py
│   ├── server.py               # MCP server entry point
│   ├── health.py               # health resource implementation
│   └── config.py               # role map, Ollama URL, port
├── docs/
│   ├── architecture.md         # transferred from munews.app
│   ├── design-the-inn-model.md # transferred from munews.app
│   ├── 2026-04-03-blog-claude-code-agents.md
│   ├── 2026-04-03-blog-the-inn-model.md
│   └── diagrams/
│       ├── inn-model.dot
│       └── inn-model.mmd
├── CLAUDE.md                   # project instructions for Claude Code
├── README.md
└── .gitignore
```

## 9. Future Roadmap (NOT v0.1)

In order of likely implementation:

1. **v0.2: More windows** — `inn://queue` (pending tasks), `inn://ledger` (stats summary)
2. **v0.3: The front door** — `submit_order` tool, task queue in SQLite
3. **v0.4: Kitchen dispatch** — inn triggers `claude --agent orchestrator` on the host
4. **v0.5: GitHub integration** — webhook receiver for labeled issues
5. **v0.6: The ledger** — task classification, cost tracking, adaptive routing
6. **v1.0: The full inn** — all roles staffed, adaptive routing, self-monitoring

## 10. Origin

daia-inn emerged from brainstorming during the munews.app project. The research, design thinking, and inn model were developed while building a multi-model agent pipeline for that project. Key documents:

- [The Inn Model — Design Document](design-the-inn-model.md) — full role taxonomy and economic model
- [It's Markdown All the Way Down](2026-04-03-01-blog-claude-code-agents.md) — how the pipeline works
- [The Inn Model — Blog Post](2026-04-03-02-blog-the-inn-model.md) — public-facing writeup
- [Directed Graph Diagrams](diagrams/) — Mermaid and Graphviz visualizations

munews.app remains the first customer of the inn — but the inn serves anyone who walks through the door.
