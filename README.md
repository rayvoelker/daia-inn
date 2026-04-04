# daia-inn

MCP server exposing the daia workstation's AI infrastructure as observable, queryable resources.

The metaphor: daia is a medieval inn. Tasks (customers) walk in, get classified, routed to the right agent (cook), and come out as accepted PRs (satisfied customers). daia-inn is the building itself — the front door, the windows to peer in, and eventually the kitchen orchestration.

## v0.1: The Watchman

The watchman's one job: look through the window and report what he sees.

- **One MCP resource:** `inn://health` — loaded models, GPU/RAM usage, Ollama status
- **Runs in:** docker-compose alongside Ollama
- **Accessible via:** Tailscale from any MCP client

## Quick Start

```bash
docker compose up -d
```

### Connect from Claude Code (local)

```json
{
  "mcpServers": {
    "daia-inn": {
      "command": "docker",
      "args": ["exec", "-i", "daia-inn-inn-1", "python", "-m", "src.server", "--stdio"]
    }
  }
}
```

### Connect from Claude Code (remote over Tailscale)

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

## Docs

- [v0.1 Design Spec](docs/daia-inn-v01-design.md)
- [The Inn Model](docs/design-the-inn-model.md) — full role taxonomy and economic model
- [It's Markdown All the Way Down](docs/blog-claude-code-agents.md) — how the agent pipeline works
- [The Inn Model — Blog Post](docs/blog-the-inn-model.md) — public-facing writeup

## Roadmap

| Version | Codename | What Ships |
|---------|----------|------------|
| v0.1 | The Watchman | Health resource, model status window |
| v0.2 | More Windows | Queue status, ledger summary resources |
| v0.3 | The Front Door | Task submission tool, SQLite queue |
| v0.4 | Kitchen Dispatch | Triggers `claude --agent orchestrator` on host |
| v0.5 | GitHub Integration | Webhook receiver for labeled issues |
| v0.6 | The Ledger | Task classification, cost tracking, adaptive routing |
| v1.0 | The Full Inn | All roles staffed, adaptive routing, self-monitoring |

## License

Private.
