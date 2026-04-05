# Repo Consolidation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace 13 contradictory docs with 3 canonical documents on main; archive all historical docs to a protected branch.

**Architecture:** Docs-only change. No code modifications. Create archive branch from current main, write two new docs (design.md, blog-the-inn.md), update design review and CLAUDE.md, delete archived files from main.

**Tech Stack:** Git, Markdown, GitHub CLI (gh)

---

### Task 1: Create Archive Branch

**Files:** None created/modified — git branch operations only.

- [ ] **Step 1: Create the archive branch from current main**

```bash
git branch archive/v0.1-design-history main
```

- [ ] **Step 2: Push the archive branch to remote**

```bash
git push origin archive/v0.1-design-history
```

- [ ] **Step 3: Verify the branch exists on remote**

```bash
git branch -r | grep archive
```

Expected: `origin/archive/v0.1-design-history`

- [ ] **Step 4: Protect the branch on GitHub**

Note: GitHub branch protection requires admin access. If `gh` API is available:

```bash
gh api repos/{owner}/{repo}/branches/archive/v0.1-design-history/protection \
  -X PUT \
  -f "required_status_checks=null" \
  -f "enforce_admins=null" \
  -f "required_pull_request_reviews=null" \
  -f "restrictions=null" 2>/dev/null || echo "Set branch protection manually in GitHub Settings > Branches"
```

If this fails, set protection manually in GitHub repo settings. This is non-blocking for the rest of the plan.

- [ ] **Step 5: Commit (no changes to commit — branch operation only)**

No commit needed. Verify with `git status` that working tree is clean.

---

### Task 2: Write Canonical Design Doc (`docs/design.md`)

**Files:**
- Create: `docs/design.md`

This is the single source of truth. Content synthesized from the design review (resolved decisions), the original design-the-inn-model.md (role taxonomy, economics), daia-inn-v01-design.md (implementation details), and new-roles-design.md (Bard, Farmer, Carter, Scribe).

- [ ] **Step 1: Write `docs/design.md`**

```markdown
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
```

- [ ] **Step 2: Commit**

```bash
git add docs/design.md
git commit -m "docs: canonical design doc — single source of truth"
```

---

### Task 3: Write Consolidated Blog Post (`docs/blog-the-inn.md`)

**Files:**
- Create: `docs/blog-the-inn.md`

One clean long-form narrative. Same voice as the existing blog posts (direct, concrete, first-person). No references to superseded thinking — just the current model presented as truth.

- [ ] **Step 1: Write `docs/blog-the-inn.md`**

The blog post should cover these topics in this order, in the author's existing voice:

1. **Opening hook** — "Most agent frameworks only think about two roles: the planner and the coder. A real software project has dozens of roles." Lead with the core insight.

2. **The metaphor** — Why a medieval inn maps to agent orchestration. A kitchen handles orders: classify, prep, cook, plate-check, serve. An inn has staff beyond the kitchen: stables (infrastructure), housekeeping (cleanup), security (enforcement). Each maps to a real pipeline task.

3. **The roster overview** — Not the full table (that's the design doc), but the key roles in plain English. The Innkeeper (orchestrator, star topology hub), the Line Cook (local model, free, does the volume work), the Scout (explores before cooking), the Head Chef (escalation target), the Chambermaid (safe cleanup only), the Waitstaff (reviewer). Mention that most "roles" are actually scripts — the Barber is just `ruff format`.

4. **The economics** — Cheap models do volume work. Expensive models make decisions. The Innkeeper is the only Opus-tier role, invoked per-task, not long-running. The ledger tracks outcomes so routing improves over time.

5. **The physical architecture** — What actually runs: three Docker containers (innkeeper, inn, ollama) and one systemd unit (the spouse). The inn is a serving window (MCP server) — it answers questions and takes orders but doesn't decide anything. The oven (Ollama) is swappable. Include the simplified ASCII layout.

6. **The spouse** — The supervisor pattern. You can't self-monitor. The spouse is a systemd timer that watches the Innkeeper container and kills/restarts on stall. She's the only thing outside Docker, and that's the point — she needs to outlive what she watches.

7. **What's built** — v0.1 "The Watchman": one MCP resource (`inn://health`), twenty tests, five modules. The first window into the kitchen.

8. **What's next** — More windows (roster, ledger), then the front door (task submission), then adaptive routing. The complexity is ahead, not behind.

Tone guidance: write like the existing blog posts. Short paragraphs. Concrete examples. No hedging. First person where natural. Roughly 1500-2500 words.

- [ ] **Step 2: Commit**

```bash
git add docs/blog-the-inn.md
git commit -m "docs: consolidated blog post — the inn model"
```

---

### Task 4: Update Design Review

**Files:**
- Modify: `docs/2026-04-04-design-review.md`

- [ ] **Step 1: Mark issue #4 as RESOLVED**

Change the heading from:

```markdown
### 4. Role Inflation — Many "Roles" Are Just Scripts or Tools
```

to:

```markdown
### 4. Role Inflation — Many "Roles" Are Just Scripts or Tools — RESOLVED
```

Add a resolution note at the end of the section:

```markdown
**Resolution:** The canonical design doc (`docs/design.md`) now splits the roster into three explicit categories: Agents (consume tokens, make decisions), Supervisor (systemd, host-level), and Tools (scripts/cron, $0, deterministic). The metaphor is preserved but the taxonomy is honest about what's an agent and what's a script.
```

- [ ] **Step 2: Update the contradictions table**

Change:

```markdown
| 20+ roles in the roster | ~6 are actually agents | Role count overstates system complexity |
```

to:

```markdown
| ~~20+ roles in the roster~~ | ~~~6 are actually agents~~ | ~~RESOLVED: design.md splits agents/supervisor/tools explicitly~~ |
```

- [ ] **Step 3: Update recommended next step #2**

Change:

```markdown
2. **Separate agents from tools in the taxonomy.** Keep the metaphor, but mark which roles are agents (make decisions, consume tokens) vs. tools (run scripts, cost nothing). The Ledger schema, the event protocol, and the Bard's scope all depend on this distinction.
```

to:

```markdown
2. ~~**Separate agents from tools in the taxonomy.**~~ RESOLVED — design.md now has three categories: Agents, Supervisor, Tools. See issue #4.
```

- [ ] **Step 4: Commit**

```bash
git add docs/2026-04-04-design-review.md
git commit -m "docs: mark role inflation issue as resolved in design review"
```

---

### Task 5: Remove Archived Files from Main

**Files:**
- Delete: 12 files from `docs/`

- [ ] **Step 1: Verify archive branch has the files**

```bash
git log archive/v0.1-design-history --oneline -1
```

Expected: shows the same commit as current main (confirming all files are preserved).

- [ ] **Step 2: Delete the blog posts**

```bash
git rm docs/2026-04-03-01-blog-claude-code-agents.md
git rm docs/2026-04-03-02-blog-the-inn-model.md
git rm docs/2026-04-03-03-blog-the-handoff.md
git rm docs/2026-04-04-04-blog-raising-the-walls.md
git rm docs/2026-04-04-05-blog-the-watchman-ships.md
git rm docs/2026-04-04-06-blog-the-bard.md
git rm docs/2026-04-04-07-blog-the-serving-window.md
```

- [ ] **Step 3: Delete the superseded design docs**

```bash
git rm docs/design-the-inn-model.md
git rm docs/daia-inn-v01-design.md
git rm docs/superpowers/specs/2026-04-04-new-roles-design.md
```

- [ ] **Step 4: Delete the completed implementation plans**

```bash
git rm docs/superpowers/plans/2026-04-03-v01-the-watchman.md
git rm docs/superpowers/plans/2026-04-04-watchman-mvp.md
```

- [ ] **Step 5: Delete old diagram PNGs (keep source files)**

```bash
git rm docs/diagrams/kitchen.png
git rm docs/diagrams/dining-room.png
git rm docs/diagrams/star-topology.png
git rm docs/diagrams/full-flow.png
```

- [ ] **Step 6: Commit**

```bash
git add -A docs/
git commit -m "docs: archive superseded docs, plans, and blog posts

All removed files preserved on branch archive/v0.1-design-history.
Canonical docs: design.md, blog-the-inn.md, design-review.md."
```

---

### Task 6: Update CLAUDE.md

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Replace the Key Docs section**

Replace the existing `## Key Docs` section (lines 47-54 of current CLAUDE.md):

```markdown
## Key Docs

- `docs/daia-inn-v01-design.md` — v0.1 design spec
- `docs/design-the-inn-model.md` — the inn model (role taxonomy, economics, adaptive routing)
- `docs/superpowers/specs/2026-04-04-new-roles-design.md` — Bard, Farmer, Carter, Scribe design spec
- `docs/2026-04-04-blog-the-watchman-ships.md` — v0.1 ship log
- `docs/2026-04-04-blog-the-serving-window.md` — MCP architecture explained (latest)
- `docs/2026-04-03-blog-claude-code-agents.md` — how the pipeline works
- `docs/2026-04-03-blog-the-inn-model.md` — public-facing writeup
```

with:

```markdown
## Key Docs

- `docs/design.md` — canonical architecture (THE source of truth)
- `docs/blog-the-inn.md` — long-form narrative for human readers
- `docs/2026-04-04-design-review.md` — open design issues

Historical design docs archived on branch `archive/v0.1-design-history`.
```

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md to point to canonical docs"
```

---

### Task 7: Final Push and Verify

**Files:** None — git operations only.

- [ ] **Step 1: Verify the docs/ directory is clean**

```bash
ls docs/
```

Expected contents:
```
2026-04-04-design-review.md
blog-the-inn.md
design.md
diagrams/
superpowers/
```

- [ ] **Step 2: Verify diagrams/ is clean**

```bash
ls docs/diagrams/
```

Expected contents:
```
inn-model.dot
inn-model.mmd
the-inn.mmd
the-inn.png
```

- [ ] **Step 3: Verify superpowers/ only has the consolidation spec and plan**

```bash
find docs/superpowers -name "*.md" | sort
```

Expected:
```
docs/superpowers/plans/2026-04-05-repo-consolidation.md
docs/superpowers/specs/2026-04-05-repo-consolidation-design.md
```

- [ ] **Step 4: Push to remote**

```bash
git push origin main
```

- [ ] **Step 5: Verify archive branch is intact**

```bash
git log archive/v0.1-design-history --oneline -3
```

Expected: shows the same commits as main had before deletions.
