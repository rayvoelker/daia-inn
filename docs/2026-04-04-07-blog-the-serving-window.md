---
title: "The Serving Window"
subtitle: "What the MCP Server Actually Is (and Isn't)"
date: 2026-04-04
series: daia-inn
order: 7
---

# The Serving Window: What the MCP Server Actually Is (and Isn't)

Someone asked me: "So the agents live inside the Docker containers?"

No. And the confusion is worth untangling, because it reveals something about how the inn is designed.

## The Inn Is Not an Agent

The MCP server is a window into the kitchen. It doesn't decide what to cook. It doesn't seat guests. It doesn't manage staff. It answers questions and, eventually, takes orders.

Right now it has one resource: `inn://health`. A client connects, asks "what's the state of the kitchen?", gets back JSON. That's it.

```
┌──────────────────────────────────────────┐
│  Docker Compose (daia-inn)               │
│                                          │
│  ┌───────────┐    ┌────────────────┐     │
│  │  Ollama    │◄───│  inn (MCP)     │     │
│  │  :11434    │    │  :3001         │     │
│  │            │    │                │     │
│  │  gemma4    │    │  inn://health  │     │
│  │  qwen3     │    │  (read-only)   │     │
│  └───────────┘    └────────────────┘     │
│                          ▲               │
└──────────────────────────┼───────────────┘
                           │ MCP protocol
                 ┌─────────┴──────────┐
                 │    MCP Clients      │
                 │                     │
                 │  Claude Code        │
                 │  Claude Desktop     │
                 │  custom scripts     │
                 │  other agents       │
                 └─────────────────────┘
```

## MCP Is a Protocol, Not a Framework

MCP defines how a client discovers and uses what a server exposes. Think USB — it says "here's how to ask what's plugged in and how to use it." The server doesn't do work on its own. It answers questions and executes tools when asked.

Two categories of things a server can expose:

- **Resources** — read-only windows. `inn://health` is the first. Eventually: `inn://roster`, `inn://ledger`.
- **Tools** — actions a client can invoke. Not yet, but this is where "run this prompt through the line cook" will live.

## Where Do Agents Fit?

They're the *clients*, not the server.

When Claude Code connects to the inn, Claude Code is the agent. It reads `inn://health` to understand what's available, then makes decisions. The inn doesn't decide anything — it serves.

When tools arrive, the flow looks like this:

```
Claude Code (agent)
  → reads inn://health     → "what models are loaded?"
  → reads inn://roster     → "who does what?"
  → calls inn.cook()       → "summarize this with the scout"
  → inn forwards to Ollama → gemma4:e4b runs the prompt
  → result returns         → Claude Code decides what to do next
```

The agents — Claude Code sessions, the future Bard, the future Innkeeper — all live *outside* the inn container. They connect over MCP. The inn is the kitchen. It has ovens and serving windows. No customers live inside it.

## Could Agents Run as Containers?

Sure. A Bard container that periodically connects via MCP, checks health, monitors worker liveness — that's a plausible future design. But it's not baked into the current architecture. The inn doesn't care whether its clients are Claude Code on a laptop, a systemd timer on the host, or another container in the same compose stack.

That's the point of a protocol. The serving window doesn't need to know who's standing on the other side.

## The Oven Note

One more architectural detail worth recording: Ollama is the current model-serving backend, but the inn treats it as swappable. The separation:

- `ollama.py` is the only file that knows Ollama exists — it fetches data and returns plain dicts
- `health.py` parses those dicts — no Ollama imports, no API knowledge
- `server.py` composes them — doesn't know how data was fetched

If the oven changes someday (vLLM, llama.cpp, TGI), you replace one file. The parsers and the server don't change. The serving window doesn't care what brand of oven is behind the wall.

---

*The inn is a kitchen, not a restaurant. It doesn't seat guests — it serves through a window. The guests decide what to order, when to eat, and whether to come back.*

---

Previously:
- [The Watchman Ships](2026-04-04-05-blog-the-watchman-ships.md) — twenty tests, one resource, the inn is open
- [Raising the Walls](2026-04-04-04-blog-raising-the-walls.md) — building with two agents and a phone
- [The Handoff](2026-04-03-03-blog-the-handoff.md) — how a link aggregator became a workstation
- [It's Markdown All the Way Down](2026-04-03-01-blog-claude-code-agents.md) — how the pipeline works
- [The Inn Model](2026-04-03-02-blog-the-inn-model.md) — the full role taxonomy and economics
