---
title: "The Watchman Ships"
subtitle: "Twenty Tests, One Resource, the Inn Is Open"
date: 2026-04-04
series: daia-inn
order: 5
---

# The Watchman Ships: Twenty Tests, One Resource, the Inn Is Open

The door is hung. The Watchman — daia-inn v0.1 — is done.

One MCP resource. `inn://health`. You connect a client, read the resource, and you get back a JSON report that tells you everything about the state of the kitchen:

```json
{
  "ollama": { "status": "running", "version": "0.20.0" },
  "models": [
    { "name": "gemma4:26b", "role": "line_cook", "location": "GPU", "status": "loaded" }
  ],
  "gpu": { "name": "NVIDIA GeForce RTX 4090", "vram_used_gb": 23.1, "vram_total_gb": 24.0 },
  "system": { "ram_used_gb": 38, "ram_total_gb": 125 }
}
```

That's the whole API. Is Ollama alive? Which models are loaded? What roles do they fill? How much VRAM and RAM are in use? Can the kitchen cook?

## The Stack

Five modules, twenty tests, 0.22 seconds:

| Module | Job | Tests |
|--------|-----|-------|
| `config.py` | Settings + role map | 3 |
| `system.py` | nvidia-smi and /proc/meminfo parsing | 4 |
| `health.py` | Ollama response parsing + report assembly | 8 |
| `ollama.py` | Async httpx client for Ollama's API | 4 |
| `server.py` | FastMCP wiring, `inn://health` resource | 1 |

The pattern that emerged: **pure parsers at the bottom, thin I/O in the middle, composition at the top.** Every parser takes a string or dict and returns a dataclass. No mocks needed. The I/O wrappers are almost too simple to break — call an API, return the dict. The server just plugs them together.

## Docker

Two containers. Ollama gets the GPU. The inn gets nvidia-smi access (for VRAM stats) and a read-only mount of `/proc/meminfo`. They talk over Docker's internal network. The inn is exposed on port 3001.

```
docker compose up -d
```

That's deployment.

## What I Noticed

The whole thing was built TDD — failing test first, minimal implementation, green, commit, next. Seven tasks in the plan, each one a self-contained module. The kind of work that's boring in the best way: no surprises, no debugging sessions, no "wait, why doesn't this work."

The most interesting decision was keeping `ollama.py` as a dumb pipe. The plan originally had it parsing responses into typed objects. But `health.py` already had the parsing logic (built in an earlier session), so the client just returns raw dicts. One layer parses, one layer fetches. No overlap.

## What's Next

The Watchman watches. That's all it does. The next role is one that *acts* — probably the Scullion (cleanup tasks) or the Bard (context distribution). But the foundation is set: MCP server running, Docker composed, tests green, health reporting live.

The inn is open. The first guest can check in.

---

*Twenty tests. Five modules. One resource. Zero surprises.*

---

Previously:
- [Raising the Walls](2026-04-04-04-blog-raising-the-walls.md) — building with two agents and a phone
- [The Handoff](2026-04-03-03-blog-the-handoff.md) — how a link aggregator became a workstation
- [It's Markdown All the Way Down](2026-04-03-01-blog-claude-code-agents.md) — how the pipeline works
- [The Inn Model](2026-04-03-02-blog-the-inn-model.md) — the full role taxonomy and economics
