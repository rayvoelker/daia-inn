# The Inn Model

## What Medieval Hospitality Teaches Us About Running AI Agents

Most agent frameworks think about two roles: the planner and the coder. Maybe a reviewer if you're feeling fancy. That's like running a restaurant with only a head chef and a waiter.

A real software project has dozens of roles. Most of the work isn't writing code. It's cleanup, maintenance, provisioning, security, dependency management, formatting, branch management, logging, and keeping the lights on. If your agent framework only models "think" and "code," you're ignoring 80% of the work.

A medieval inn turns out to be a surprisingly complete model for all of it.

## The Metaphor

An inn isn't just a kitchen. It's a complete operation:

- **The kitchen** handles orders. Classify the dish, prep the ingredients, cook it, plate-check it, serve it. This is the implementation pipeline.
- **The stables** receive horses, set up workspaces, clean up after departures. This is infrastructure — branches, worktrees, Docker containers, disk space.
- **Housekeeping** cleans rooms, washes linens, replaces rushes on the floor. This is code cleanup — dead imports, stale branches, orphaned processes, formatting.
- **Security** keeps the peace. The bouncer checks credentials at the door. The strong-arm enforces rules. This is capability enforcement, pre-commit hooks, contract validation.
- **The back office** keeps the books, tracks costs, writes letters. This is the ledger, the commit messages, the PR descriptions, the documentation.

Every role in the inn maps to a real task in a software pipeline. The insight isn't that the metaphor is cute — it's that it's *complete*. Once you start mapping roles, you find that every gap in your pipeline has a medieval equivalent.

## The Roster

The inn has about 25 named roles. Here are the ones that matter most:

**The Innkeeper** is the orchestrator. Opus, the most expensive model, running as the hub of a star topology. Every decision of consequence flows through the Innkeeper — task classification, worker dispatch, failure reclassification, context accumulation. It doesn't do the cooking. It decides *who* cooks, *what* they cook, and *whether to send the plate back*.

**The Line Cook** is the workhorse. A local gemma4:26b model running on the GPU at 50 tokens per second. Free. Handles standard implementation work — takes test specs, produces code. The vast majority of tasks land here.

**The Scout** runs reconnaissance before anyone starts cooking. A small gemma4:e4b model on CPU at 13 tokens per second. Also free. It explores the codebase, finds relevant files, identifies patterns and conventions. The cook shouldn't waste time figuring out where things are.

**The Head Chef** is Sonnet — the escalation target. When the Line Cook gets stuck after three attempts, the Innkeeper sends the order up. More expensive, more capable, handles the cross-file refactors and architectural work that local models struggle with.

**The Chambermaid** cleans up after the cook. A cheap Haiku model that handles lint fixes, format cleanup, dead code removal. Critically: restricted to provably-safe transforms only. The chambermaid never makes semantic changes. If `ruff` wouldn't do it, neither does the chambermaid.

**The Waitstaff** reviews every plate before it reaches the customer. Sonnet, inspecting for real design issues — not formatting (the chambermaid already handled that). The reviewer only sees substantive problems.

Here's the thing most people miss: about half the roles aren't agents at all. They're scripts. The Barber is `ruff format`. The Strong-arm is pre-commit hooks. The Bouncer is kernel capabilities. The Fire-tender is a cron job that pings Ollama to keep models loaded. Calling them "roles" helps you think about what your pipeline needs. But when you build the system, you don't need 25 AI agents — you need about 15 agents and 10 scripts.

The roster splits into three categories:
- **Agents** — consume tokens, make decisions (Innkeeper, cooks, reviewers, scribes)
- **Supervisor** — the Innkeeper's Spouse, a systemd unit that watches the Innkeeper (more on this below)
- **Tools** — scripts, cron jobs, formatters, hooks ($0, deterministic, no AI needed)

## The Economics

Cost is the architecture. The most important design decision isn't which models to use — it's *when* to use the expensive ones.

| Tier | Models | Cost | Use For |
|------|--------|------|---------|
| Free | Local gemma4:26b, e4b | $0 | Volume work — coding, scouting |
| Cheap | Haiku | ~$0.001/task | Prep, cleanup, scribing |
| Moderate | Sonnet | ~$0.01/task | Review, escalation, docs |
| Expensive | Opus | ~$0.10/task | Innkeeper only |
| Tools | Scripts, cron | $0 | Formatting, CI, cleanup |

The Innkeeper is per-task, not long-running. Each task is a fresh `claude -p` invocation. It reads the ledger, classifies the task, dispatches workers, accumulates context, writes results, and exits. The ledger is the Innkeeper's persistent memory, not the context window.

Over time, the ledger reveals patterns: "The Line Cook handles utility modules 95% of the time — stop sending those to the Head Chef." "Cross-file refactors need Sonnet first try — skip the local model." This is a multi-armed bandit optimization, and the ledger is the reward signal.

## The Physical Architecture

Here's what actually runs:

```
┌─ daia-ts host ─────────────────────────────────────┐
│                                                     │
│  systemd                                            │
│  ├── innkeeper-spouse.timer      ← heartbeat (30s)  │
│  ├── innkeeper-spouse.service    ← kills/restarts   │
│  │                                                  │
│  └── docker compose                                 │
│      ├── innkeeper  (claude -p, per-task)            │
│      ├── inn        (MCP server :3001)               │
│      └── ollama     (oven :11434)                    │
│                                                     │
│  Hardware: RTX 4090 (24GB), 124GB RAM, 32 cores     │
└─────────────────────────────────────────────────────┘
```

Three Docker containers and one systemd unit. That's the whole inn.

The **inn** is an MCP server — a serving window into the kitchen. It exposes resources (read-only windows like `inn://health`) and tools (actions like `inn.cook()`). It doesn't decide anything. It answers questions and takes orders. MCP is a protocol, not a framework — it defines how clients discover and use what servers expose. Think USB.

The **oven** is Ollama, but the architecture treats it as swappable. One file — `ollama.py` — knows Ollama exists. Everything else works with plain dicts and strings. To swap to vLLM or llama.cpp, you replace one file. The parsers and the server don't change.

The **innkeeper** runs `claude -p` in a container with an API key and a CLAUDE.md that contains the orchestration logic. The inn model, expressed as markdown, is the Innkeeper's brain.

## The Spouse

Here's a problem: the Innkeeper might die. The process runs, the spinner spins, but tokens stop flowing. I've watched it happen — a Claude session stalls mid-task, and nobody notices until you check the terminal twenty minutes later.

The Innkeeper can't monitor itself. If it's the one that stalled, who reports the stall?

The Innkeeper's Spouse is a systemd timer on the host. She runs every 30 seconds, checks the Innkeeper container's logs, and kills the process if there's been no output for 120 seconds. She enforces budget limits and timeouts. She writes a structured record of every intervention.

She's the only thing that lives outside Docker, and that's the point. She needs to outlive what she watches. If the Innkeeper's container crashes, she's still running. If Docker restarts, she's still running. systemd manages Docker, not the other way around.

This is the supervisor pattern from Erlang/OTP: you can't self-monitor, so someone outside holds the kill switch. The spouse is a bash script today. She could be upgraded to a Haiku model later for smarter "stuck vs. thinking" judgment. But the architecture is the same: one thing outside, watching everything inside.

## What's Built

v0.1 is called "The Watchman." It ships one MCP resource: `inn://health`. A client connects, asks "what's the state of the kitchen?", and gets back JSON — which models are loaded, GPU and RAM usage, Ollama health status.

Twenty tests across five modules. Config, system stats, health report assembly, Ollama client, MCP server. The pattern is clean: pure parsers at the bottom, thin I/O in the middle, composition at the top.

```bash
docker compose up -d    # start the inn
# connect any MCP client to localhost:3001
```

It's accessible locally or over Tailscale from any device on the tailnet. The Watchman watches. That's all it does.

## What's Next

The Watchman is a window. The next step is more windows — `inn://roster` (who does what), `inn://ledger` (what happened). Read-only resources. Still just watching.

Then comes the front door: task submission via MCP tools. This is where the real orchestration begins. Classification, routing, dispatch, monitoring, feedback handling. Everything in the Innkeeper's job description. This is v0.3, and it's where the design gets tested against reality.

After that, adaptive routing — the Innkeeper reading the ledger before making decisions, learning which cook handles which dish. GPU scheduling becomes real (one 4090, one model at a time — the "parallel kitchen" is really "parallel prep + sequential cooking"). Context accumulation costs become measurable. The cold start problem for the ledger needs a solution.

The complexity is ahead, not behind. The Watchman proves the foundation works. The next roles are the ones that act.

---

*A well-run inn doesn't need its best cook on every dish. It needs the right cook on each dish, and a good enough ledger to know the difference.*
