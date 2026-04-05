# daia-inn Design

> Canonical architecture document. This is the single source of truth for how the inn works.
> Last updated: 2026-04-05.

## Overview

daia-inn is an MCP server exposing a workstation's AI infrastructure. It runs alongside Ollama in docker-compose and is accessible locally or over Tailscale. The system uses a medieval inn metaphor: tasks (orders) come in, get classified and routed to the right worker (cook), and come out as shipped PRs. The inn doesn't decide what to cook — it provides the kitchen, the ovens, and the serving window. Agents connect as MCP clients and make the decisions.

## Physical Architecture

```
┌─ daia-ts host ──────────────────────────────────────────────────────────┐
│                                                                         │
│  SYSTEMD (above everything — survives container crashes)                │
│  ┌────────────────────────────────────────────────────────┐             │
│  │  THE INNKEEPER'S SPOUSE                                │             │
│  │  innkeeper-spouse.timer  → runs every 30s              │             │
│  │  innkeeper-spouse.service → checks logs, kills/restarts│             │
│  │                            enforces budget & timeouts  │             │
│  └──────────────────────────────┬─────────────────────────┘             │
│                                 │ docker logs / restart                  │
│                                 ▼                                        │
│  DOCKER COMPOSE ────────────────────────────────────────────────────    │
│  │                                                                 │    │
│  │  ┌─────────────────────┐   ┌──────────────────────────────┐     │    │
│  │  │  innkeeper           │   │  inn (MCP server :3001)      │     │    │
│  │  │                      │   │                              │     │    │
│  │  │  claude -p            │──►│  Resources (windows):       │     │    │
│  │  │  (per-task)          │MCP│    inn://health    ✓ live    │     │    │
│  │  │                      │   │    inn://roster   ○ future   │     │    │
│  │  │  Reads ledger        │   │    inn://ledger   ○ future   │     │    │
│  │  │  Classifies task     │   │                              │     │    │
│  │  │  Dispatches workers  │   │  Tools (actions):            │     │    │
│  │  │  Accumulates context │   │    inn.cook()     ○ future   │     │    │
│  │  │  Exits when done     │   │    inn.dispatch() ○ future   │     │    │
│  │  │                      │   │                              │     │    │
│  │  │  Needs:              │   │  Code:                       │     │    │
│  │  │   ANTHROPIC_API_KEY  │   │    server.py  (composition)  │     │    │
│  │  │   CLAUDE.md (prompt) │   │    health.py  (parsing)      │     │    │
│  │  └──────────┬───────────┘   │    system.py  (GPU/RAM)      │     │    │
│  │             │               │    ollama.py  (I/O client)   │     │    │
│  │             │               └──────────┬───────────────────┘     │    │
│  │             │                          │ HTTP                    │    │
│  │             │               ┌──────────▼───────────────────┐     │    │
│  │             │               │  ollama (oven :11434)         │     │    │
│  │             │               │                              │     │    │
│  │             │               │  gemma4:26b    → GPU  50t/s  │     │    │
│  │             │               │  (line cook)                 │     │    │
│  │             │               │                              │     │    │
│  │             │               │  gemma4:e4b    → CPU  13t/s  │     │    │
│  │             │               │  (scout)                     │     │    │
│  │             │               └──────────────────────────────┘     │    │
│  │             │                                                    │    │
│  │             │  ┌──────────────────────────┐                      │    │
│  │             └─►│  Ledger (shared volume)   │                      │    │
│  │                │  Task records, costs,     │                      │    │
│  │                │  routing history           │                      │    │
│  │                └──────────────────────────┘                      │    │
│  └──────────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  HARDWARE                                                               │
│  ├── RTX 4090 (24GB VRAM) ← one GPU model at a time                    │
│  ├── 124GB RAM, 32 cores  ← CPU models run here                        │
│  └── Tailscale (daia.tailnet)                                           │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
         │                              ▲
         │ outbound API calls           │ inbound MCP (via Tailscale)
         ▼                              │
  ┌──────────────┐              ┌───────┴────────┐
  │ Anthropic API │              │  MCP Clients    │
  │               │              │                 │
  │ Opus ($$$$)   │              │  Claude Code    │
  │ Sonnet ($$)   │              │  Claude Desktop │
  │ Haiku ($)     │              │  Custom scripts │
  └──────────────┘              └─────────────────┘
```

**Authority hierarchy:**

| Layer | Who | Can do |
|-------|-----|--------|
| systemd | Spouse | Kill/restart all containers. Budget enforcement. The only thing outside Docker. |
| Docker | Innkeeper | Read MCP resources, call tools, dispatch to oven. Per-task lifecycle. |
| Docker | Inn (MCP) | Serve resources, execute tools. No decisions — just answers and actions. |
| Docker | Ollama (oven) | Run prompts through loaded models. Swappable backend. |
| External | Human / clients | Connect via Tailscale, read resources, invoke tools. |

## The Innkeeper

The Innkeeper is Claude Code running headless (`claude -p`) in a Docker container. It connects to the inn as an MCP client.

**Per-task, not long-running.** Each task is a fresh `claude -p` invocation. The Innkeeper reads the ledger, classifies the task, dispatches workers, accumulates context across stages, and writes results back to the ledger — then exits. The ledger is the Innkeeper's persistent memory, not the context window.

**The Innkeeper container needs:**
- `ANTHROPIC_API_KEY` in its environment
- Network access to `api.anthropic.com` (outbound) and the `inn` service (inbound MCP)
- A CLAUDE.md or prompt that defines the orchestration logic — the inn model as markdown

### The Innkeeper's Spouse

The spouse is a systemd unit on the host — the only role that lives outside the containerized world. She supervises the Innkeeper container using the Erlang/OTP supervisor pattern: you can't self-monitor, so someone outside holds the kill switch.

```ini
# innkeeper-spouse.timer
[Timer]
OnBootSec=60
OnUnitActiveSec=30s

# innkeeper-spouse.service (Type=oneshot)
# - check innkeeper container logs for recent output
# - if no tokens for 120s: docker restart innkeeper
# - if cost > budget: docker stop innkeeper
# - write structured record of any intervention
```

**What the spouse does:**
- Kills and restarts the Innkeeper on stall (no output for 120s)
- Enforces budget limits per task
- Enforces timeouts based on ledger history
- Initially a bash script; upgradeable to Haiku for smarter judgment

## The Inn (MCP Server)

The inn is a Python MCP server (FastMCP). It doesn't decide anything — it serves resources and executes tools when asked.

**Resources (read-only windows):**
- `inn://health` — model status, GPU/RAM usage, Ollama health (v0.1, live)
- `inn://roster` — model capabilities and role assignments (future)
- `inn://ledger` — task history, costs, routing outcomes (future)

**Tools (actions):**
- `inn.cook()` — run a prompt through a specific model (future)
- `inn.dispatch()` — submit a task for pipeline processing (future)

### The Oven Abstraction

Ollama is the current model-serving backend, but the architecture treats it as swappable:

- **`ollama.py`** — the only file that knows Ollama exists. Fetches data, returns plain dicts.
- **`health.py`**, **`system.py`** — parsers. Work on raw dicts and strings. No Ollama imports.
- **`server.py`** — composes parsers and I/O. Doesn't know how data was fetched.

To swap backends (vLLM, llama.cpp, TGI), replace `ollama.py`. Parsers and server don't change.

### Source Module Layout

```
src/
├── __init__.py
├── __main__.py      → entry point (runs mcp.run)
├── server.py        → MCP server, resource handlers (composition layer)
├── config.py        → Config dataclass, role map, env var overrides
├── health.py        → Health report assembly, Ollama response parsing
├── system.py        → GPU stats (nvidia-smi), RAM stats (/proc/meminfo)
└── ollama.py        → Async HTTP client for Ollama API (I/O layer)
```

## Role Taxonomy

The inn model maps software pipeline roles to medieval inn roles. There are three categories:

### Agents (consume tokens, make decisions)

| Inn Role | Pipeline Role | Model/Tier | What It Does |
|----------|--------------|------------|--------------|
| **Innkeeper** | Orchestrator | Opus ($$$) | Classifies tasks, manages budget, dispatches workers, reclassifies on failure. The star topology hub — every decision flows through it. Only cooks as last resort. |
| **Line Cook** | Coder | gemma4:26b (free) | Standard implementation. Takes test specs, produces code. 50 tok/s on GPU. |
| **Scout** | Codebase explorer | gemma4:e4b (free) | Reconnaissance before cooking. Explores codebase, finds relevant files and patterns. 13 tok/s on CPU. |
| **Head Chef** | Escalation coder | Sonnet ($$) | Complex work the Line Cook can't handle. Cross-file refactors, architecture. |
| **Owner Cooks** | Last resort | Opus ($$$) | Only when Head Chef also fails. The most expensive option. |
| **Kitchen Boy** | Prep coder | Haiku ($) | Scaffolding, boilerplate, file creation, imports, type stubs. |
| **Baker** | Scaffolder | Haiku ($) | Module skeletons, test templates, config files. Repetitive, standardized. |
| **Chambermaid** | Code cleaner | Haiku ($) | Lint fixes, format cleanup, dead code removal. Restricted to provably-safe transforms only — never semantic changes. |
| **Waitstaff** | Reviewer | Sonnet ($$) | Inspects every plate. Real design issues only (chambermaid handled the rest). |
| **Scribe** | Commit/PR writer | Haiku ($) | Commit messages, PR descriptions, final task stats to ledger. Stamps every entry with inn git SHA. |
| **Minstrel** | Doc writer | Sonnet ($$) | Documentation, changelogs, release notes. |
| **Bard** | Observer/genealogist | Haiku ($) | Watches worker liveness (heartbeat), tracks task lineage, writes elegies for dead workers, opens/closes inn sessions. Two input channels: independent observation + events from Innkeeper. |
| **Farmer** | Model curator | Haiku/Sonnet | Watches for new model releases, compares against roster, presents candidates to Innkeeper. Doesn't download or decide. |
| **Farrier** | Dependency doctor | Sonnet ($$) | Security patches, version updates, dependency conflicts. Weekly. |
| **Carter** | Fetcher/inspector | Script + Haiku | Downloads dependencies, model weights, API specs. Scans fetched files for safety (checksums, signatures, vulnerability checks). |

### Supervisor (systemd, host-level)

| Inn Role | Pipeline Role | Implementation | What It Does |
|----------|--------------|---------------|--------------|
| **Spouse** | Innkeeper supervisor | Bash script (systemd timer) | Monitors Innkeeper container. Kills on stall, enforces budget/timeouts. Upgradeable to Haiku for smarter judgment. The only role outside Docker. |

### Tools (scripts/cron, $0, deterministic)

| Inn Role | Pipeline Role | Implementation | What It Does |
|----------|--------------|---------------|--------------|
| **Barber** | Formatter | `ruff format` / `prettier` | Applies formatting rules mechanically. |
| **Bouncer** | Capability enforcer | Kernel / containers | Checks contracts at the door. Capability enforcement. |
| **Strong-arm** | Pre-commit hooks | Git hooks | Blocks bad commits. Validates standards. |
| **Ostler** | Workspace manager | Script | Creates branches, sets up worktrees. |
| **Stable Boy** | Workspace cleaner | Script | Cleans build caches, prunes Docker images. |
| **Rushman** | Branch cleaner | Script | Deletes merged branches, cleans worktrees, rotates logs. |
| **Fire-tender** | Keepalive | Cron | Pings Ollama to keep models loaded, refreshes tokens. |
| **Lamplighter** | Logger | Script/Hook | Ensures logging is working, metrics flowing. |
| **Dung Collector** | Garbage collection | Cron | Docker prune, old model weights, orphaned processes. |
| **Spit-boy** | CI runner | Script | Runs builds, runs tests, reports pass/fail. |

## Economics

| Tier | Models | Cost | Speed | Use For |
|------|--------|------|-------|---------|
| **Free** | Local gemma4:26b, e4b | $0 | 13-50 tok/s | Volume work, always-on roles |
| **Cheap** | Haiku | ~$0.001/task | Fast | Prep, cleanup, scribing, observation |
| **Moderate** | Sonnet | ~$0.01/task | Fast | Head chef, reviewer, farrier, minstrel |
| **Expensive** | Opus | ~$0.10/task | Slower | Innkeeper only (per-task invocation) |
| **Tools** | Scripts, cron, hooks | $0 | Instant | Formatting, cleanup, CI, keepalive |

### The Ledger

The Innkeeper reads the ledger before making routing decisions. Over time, it reveals which cook handles which task type best (a multi-armed bandit optimization):

```yaml
task: slugify utility
task_type: new_feature
task_complexity: standard
cook: line_cook (gemma4:26b)
escalation_chain: [gemma4:26b]
cost_breakdown:
  orchestrator: {model: opus, tokens: 4500, cost_usd: 0.08}
  coder: {model: gemma4:26b, tokens: 3400, cost_usd: 0.00}
  reviewer: {model: sonnet, tokens: 2100, cost_usd: 0.02}
customer_satisfaction: 1.0
inn_version: {git_sha: ac67ad5}
```

### The Pipeline Flow

```
New Order → Innkeeper classifies (consults ledger)
  → Scout explores codebase
  → Baker/Kitchen Boy preps (scaffolding, stubs)
  → Line Cook implements (escalates to Head Chef → Owner if stuck)
  → Chambermaid cleans (safe transforms only)
  → Waitstaff reviews
  → Customer (tests) accepts or sends back
  → Scribe writes commit message + ledger entry
  → Shipped
```

On failure: the Innkeeper re-evaluates (not automatic retry). May reclassify complexity, re-dispatch scout, switch cook, or rewrite tests.

## Current State (v0.1 — The Watchman)

**What's implemented:**
- One MCP resource: `inn://health` returning JSON (Ollama status, loaded models, GPU/RAM usage)
- Five modules: config (3 tests), system (4 tests), health (8 tests), ollama (4 tests), server (1 test) = 20 tests
- Docker deployment: `docker compose up -d` (inn + Ollama, GPU-enabled)
- Accessible locally or via Tailscale

**Current roster:**

| Role | Model | Location | Speed |
|------|-------|----------|-------|
| Line Cook | gemma4:26b | GPU | 50 tok/s |
| Scout | gemma4:e4b-cpu | CPU/RAM | 13 tok/s |

## Roadmap

```
v0.1: The Watchman — health resource (done)
v0.2: More windows — roster resource, ledger resource
v0.3: Front door — task submission via MCP tools
      (This is where orchestration begins. Classification, routing,
       dispatch, monitoring, feedback — the core of the inn model.)
v0.4: Kitchen dispatch — adaptive routing, escalation chains
      (Hidden complexity: GPU scheduling, parallel kitchen, context
       accumulation cost, cold start for the ledger.)
v0.5: GitHub integration — PR creation, issue tracking
v0.6: Ledger analytics — routing optimization, cost tracking
v1.0: Full inn — all roles active, adaptive routing, self-improving
```

Note: v0.3-v0.4 contain the majority of the design's complexity. See the [design review](2026-04-04-design-review.md) for open issues.
