# Repo Consolidation — Design Spec

> Spec date: 2026-04-05. Status: approved design, pending implementation.

## Problem

The docs/ directory contains 13 markdown files written over two days of rapid design iteration. Blog posts, brain-dump design docs, implementation plans, and a design review coexist — and they contradict each other on key decisions (Innkeeper identity, Bard implementation, cost model, role taxonomy). Future Claude Code sessions reading these files will be grounded in stale or conflicting context, leading to inconsistent work.

## Goal

One clean, canonical set of documents on main. All historical docs preserved on a protected archive branch. Future sessions get truth, not archaeology.

## What Changes

### 1. Archive Branch

Create a protected branch `archive/v0.1-design-history` from current main before any deletions. This preserves all historical docs exactly as they are.

**Files removed from main (preserved on archive branch):**

| File | Reason |
|------|--------|
| `2026-04-03-01-blog-claude-code-agents.md` | Superseded by consolidated blog post |
| `2026-04-03-02-blog-the-inn-model.md` | Superseded by consolidated blog post |
| `2026-04-03-03-blog-the-handoff.md` | Superseded by consolidated blog post |
| `2026-04-04-04-blog-raising-the-walls.md` | Superseded by consolidated blog post |
| `2026-04-04-05-blog-the-watchman-ships.md` | Superseded by consolidated blog post |
| `2026-04-04-06-blog-the-bard.md` | Superseded by consolidated blog post |
| `2026-04-04-07-blog-the-serving-window.md` | Superseded by consolidated blog post |
| `design-the-inn-model.md` | Brain-dump, partially superseded by design review |
| `daia-inn-v01-design.md` | Implemented spec, captured in new design doc |
| `superpowers/specs/2026-04-04-new-roles-design.md` | Partially superseded, captured in new design doc |
| `superpowers/plans/2026-04-03-v01-the-watchman.md` | Completed implementation plan |
| `superpowers/plans/2026-04-04-watchman-mvp.md` | Completed implementation plan |

### 2. New Canonical Design Doc (`docs/design.md`)

The single source of truth for the system architecture. What future Claude Code sessions read.

**Sections:**

1. **Overview** — What daia-inn is. The inn metaphor in one paragraph.
2. **Physical Architecture** — ASCII diagram showing three layers: systemd (spouse), Docker (innkeeper + inn + oven), external clients. The authority hierarchy table.
3. **The Innkeeper** — Claude Code headless (`claude -p`) in a container. Per-task lifecycle. Ledger as persistent memory. The spouse as systemd supervisor (timer + service). What the spouse does (kill stalls, enforce budget, enforce timeouts).
4. **The Inn (MCP Server)** — Resources (health live, roster/ledger future). Tools (cook/dispatch future). The oven abstraction (ollama.py is the only coupled file). Source module layout (server.py → health.py → ollama.py/system.py).
5. **Role Taxonomy** — Full roster split into two clear categories:
   - **Agents** (consume tokens, make decisions): Innkeeper, Line Cook, Scout, Head Chef, Owner Cooks, Kitchen Boy, Baker, Chambermaid, Waitstaff, Scribe, Minstrel, Bard, Farmer, Farrier, Carter
   - **Supervisor** (systemd, bash initially, upgradeable to Haiku): Spouse
   - **Tools** (scripts/cron, $0, deterministic): Barber, Bouncer, Strong-arm, Ostler, Stable Boy, Rushman, Fire-tender, Lamplighter, Dung Collector, Spit-boy
6. **Economics** — Cost tiers (free/cheap/moderate/expensive/tools). The ledger concept. Adaptive routing. Updated to reflect per-task Innkeeper invocation.
7. **Current State** — v0.1 Watchman: what's implemented, current roster (Line Cook, Scout), test count, module layout.
8. **Roadmap** — v0.2 through v1.0 with honest complexity notes.

**Sources:** Draws from `design-the-inn-model.md` (role taxonomy, economics, hidden complexity), `daia-inn-v01-design.md` (implementation details), `new-roles-design.md` (Bard, Farmer, Carter, Scribe expansions), and the design review (resolved decisions on Innkeeper, spouse, Bard).

### 3. New Blog Post (`docs/blog-the-inn.md`)

One clean long-form narrative for human readers. Tells the story of the inn model without referencing the design process or superseded thinking.

**Covers:**
- The core insight (most software work isn't code — it's everything else)
- The medieval inn as an orchestration model
- The role taxonomy in plain English
- The star topology (Innkeeper as hub)
- The economics (cheap models do volume, expensive models decide)
- The physical architecture (what runs where)
- The spouse (supervisor pattern)
- The serving window (MCP as protocol)
- What's built (v0.1) and where it's heading

**Tone:** Direct, concrete, first-person. Same voice as the existing blog posts. No "we originally thought X" — just the current model presented as truth.

### 4. Updated Design Review (`docs/2026-04-04-design-review.md`)

Stays on main as the open issues tracker. Updates:
- Issue #4 (role inflation): mark RESOLVED once design doc splits agents from tools
- All other resolved/partially resolved issues: keep as-is
- Remaining open issues (#2, #5, #6, #7, #8, #9): unchanged

### 5. CLAUDE.md Update

Replace the "Key Docs" section with:

```markdown
## Key Docs

- `docs/design.md` — canonical architecture (THE source of truth)
- `docs/blog-the-inn.md` — long-form narrative for human readers
- `docs/2026-04-04-design-review.md` — open design issues

Historical design docs archived on branch `archive/v0.1-design-history`.
```

Remove all references to archived files.

### 6. Diagrams

- Keep `docs/diagrams/the-inn.mmd` and `docs/diagrams/the-inn.png` (current architecture)
- Keep `docs/diagrams/inn-model.dot` and `docs/diagrams/inn-model.mmd` (pipeline flow — still valid)
- Archive the rendered PNGs from old diagrams (kitchen.png, dining-room.png, star-topology.png, full-flow.png) — they can be re-rendered from the .dot/.mmd sources if needed

## Implementation Order

1. Create archive branch from current main, push, protect
2. Write `docs/design.md` (canonical design doc)
3. Write `docs/blog-the-inn.md` (consolidated blog post)
4. Update `docs/2026-04-04-design-review.md` (mark #4 resolved)
5. Remove archived files from main
6. Update CLAUDE.md
7. Clean up old diagram PNGs
8. Commit and push

## What This Does NOT Do

- Does not change any code (src/, tests/, docker-compose.yml, etc.)
- Does not resolve the remaining 6 open design issues (#2, #5, #6, #7, #8, #9)
- Does not change the README.md (should be updated separately to point to new docs)
