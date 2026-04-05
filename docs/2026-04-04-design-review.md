# Design Review: daia-inn

> Review date: 2026-04-04. Status: open issues, pending resolution.
> Scope: full design review covering code, specs, blog posts, and architecture.

## The Inn — Physical Architecture

> Full Mermaid diagram: [`docs/diagrams/the-inn.mmd`](diagrams/the-inn.mmd)

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

---

## What's Strong

**The v0.1 code is excellent.** Clean separation (parsers don't import I/O, I/O doesn't import domain logic, server composes). The oven abstraction is real, not aspirational — `ollama.py` is genuinely the only Ollama-coupled file. Tests are thorough. This is a solid foundation.

**The metaphor earns its keep.** It's not decoration — it actually helps reason about role boundaries. "Is the chambermaid making semantic changes?" is a clearer question than "should the cleanup pass modify logic?" The roles map to real pipeline tasks.

**The "Hidden Complexity" section is the best part of the design.** Most designs pretend the hard problems don't exist. This one names them: the Scribe Problem, feedback reclassification, chambermaid-reviewer tension, GPU contention, scout fan-out. That self-awareness is rare and valuable.

---

## Issues That Need Resolution

### 1. The Innkeeper Identity Crisis — RESOLVED

**Original question:** Who is the Innkeeper? The design described it as "the star topology hub" but never specified where it lives.

**Resolution:** The Innkeeper is Claude Code running headless (`claude -p`) in a Docker container within the compose stack. It connects to the inn as an MCP client, reads resources (`inn://health`, `inn://roster`, `inn://ledger`), and dispatches work to local models via Ollama through MCP tools.

```
┌─ daia-ts host ─────────────────────────────────────┐
│                                                     │
│  systemd                                            │
│  ├── innkeeper-spouse.service    ← watches him      │
│  ├── innkeeper-spouse.timer      ← heartbeat loop   │
│  │                                                  │
│  └── docker compose                                 │
│      ├── ollama        (oven)                       │
│      ├── inn           (MCP server)                 │
│      └── innkeeper     (claude -p)                  │
│                                                     │
└─────────────────────────────────────────────────────┘
```

**The Innkeeper container needs:**
- `ANTHROPIC_API_KEY` in its environment
- Network access to `api.anthropic.com` (outbound) and the `inn` service (inbound MCP)
- A CLAUDE.md or prompt that defines the orchestration logic — the inn model as markdown

**Per-task, not long-running.** Each task is a fresh `claude -p` invocation. The Innkeeper reads the ledger, classifies, dispatches, monitors, writes results, and exits. The ledger is the Innkeeper's persistent memory, not the context window. This avoids context window overflow and stale state.

**The Innkeeper's Spouse** is a systemd unit on the host — the only role that lives *outside* the containerized world. She supervises the Innkeeper container:

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

The spouse lives at the systemd layer because she needs to **outlive and restart** the Innkeeper. If she were inside a container, she'd die when he does. systemd is the right level — it manages Docker, not the other way around.

**What the spouse does that no other role can:**
- Kills and restarts the Innkeeper on stall (the Bard only *informs*, the spouse *acts*)
- Enforces budget limits ("you've spent $0.40 on a $0.10 task — you're done")
- Enforces timeouts ("10 minutes on a task the ledger says takes 3 — escalate or stop")

**Authority hierarchy:**

| Layer | Who | Authority |
|-------|-----|-----------|
| systemd (host) | Spouse | Can kill/restart everything below |
| Docker | Innkeeper, Inn, Ollama | Can dispatch work, manage pipeline |
| MCP | Workers via Inn | Can cook, clean, review |

The spouse is the supervisor pattern (Erlang/OTP style). You can't self-monitor — someone outside has to hold the kill switch. Initially a bash script; could later use Haiku ($0.001/check) for smarter "stuck vs. thinking" judgment.

**What this resolves:**
- The Innkeeper has a concrete home (container) and lifecycle (per-task invocation)
- The star topology hub is real infrastructure, not a conceptual role
- The spouse provides the independent liveness monitoring that the Bard spec needed but couldn't cleanly implement for the Innkeeper itself

### 2. Star Topology vs. Cost Efficiency — Fundamental Tension

The design says two things that contradict:

> "Every meaningful interaction flows through the Innkeeper" (star topology)

> "The expensive model touches as few tokens as possible" (cost efficiency)

The Innkeeper is Opus ($0.10/task). If every scout dispatch, every feedback reclassification, every context handoff, every scribe narrative goes through Opus, you're burning expensive tokens on routing, not just judgment. The design acknowledges the Innkeeper "makes the most decisions" but doesn't quantify how many Opus calls a single task actually requires.

A standard task through the full pipeline hits the Innkeeper at least 5-6 times: classify, dispatch scout, receive scout results, dispatch cook, handle feedback, hand narrative to scribe. That's $0.50-0.60 in Opus tokens per task, not $0.10.

**The question:** Can some of these routing decisions be downgraded? Could a "shift manager" (Sonnet) handle routine routing while Opus only handles reclassification and complex judgment? The design doesn't explore this, but the economics demand it.

### 3. The Bard's Implementation Contradicts the Architecture — PARTIALLY RESOLVED

The Bard spec says:

> Implementation: `bard-open.service`, `bard-heartbeat.timer`, `bard-close.service` (systemd units)

But the inn runs in Docker. The Bard needs to:
- Read `inn://health` (MCP client connecting to a Docker container)
- Monitor agent liveness (checking tmux panes? process stdout? Docker logs?)
- Write to the ledger (where? filesystem? database? another MCP resource?)

systemd units on the host watching Docker containers crosses the container abstraction boundary. The blog post acknowledges this loosely ("A Bard container that periodically connects via MCP... is a plausible future design") but the spec commits to systemd.

More fundamentally: the Bard monitors "active agents" — but where do agents run? If they're Claude Code sessions on a laptop, the Bard can't observe them from the server. If they're containers, it can watch Docker. If they're tmux panes (as in the "Raising the Walls" blog), it's fragile host-level scripting. The liveness mechanism is TBD, and it's the Bard's entire reason to exist.

**Partial resolution:** The Innkeeper's spouse (issue #1) now handles the hardest part — Innkeeper liveness — as a systemd unit on the host. This is clean because the spouse only monitors one local container. The Bard's remaining scope is worker liveness (agents dispatched by the Innkeeper), which are also containers in the compose stack. The Bard-as-systemd concern is reduced: the Bard could be a container in the compose stack that monitors sibling containers via Docker's API, rather than needing host-level systemd. The spouse handles the host-level supervision; the Bard stays inside Docker.

### 4. Role Inflation — Many "Roles" Are Just Scripts or Tools

The roster lists 20+ roles, but many aren't agents at all:

| "Role" | What it actually is |
|--------|-------------------|
| Barber | `prettier` / `ruff format` |
| Strong-armed servant | pre-commit hooks |
| Spit-boy | CI runner |
| Rushman | `git branch -d` script |
| Stable boy | `docker system prune` |
| Fire-tender | cron keepalive ping |
| Lamplighter | logging config |
| Bouncer | kernel capabilities |

Calling `ruff format` a "Barber" is charming in a blog post but potentially confusing in a spec. When you say "the inn has 20+ roles," it sounds like 20+ agents. In reality it's ~6 agents and ~15 scripts/tools. The design acknowledges this in the roster table ("Script / Cron") but the narrative treats them all as equivalent actors.

**The risk:** When you design the Ledger schema, the routing logic, and the event system, do scripts get the same event protocol as agents? Does the "Barber" emit genealogy events to the Bard? If not, the role taxonomy is misleading about the system's actual complexity.

### 5. The Role Map Undermines the Oven Abstraction

`config.py` has:

```python
ROLE_MAP = {
    "gemma4:26b": "line_cook",
    "gemma4:e4b-cpu": "scout",
    ...
}
```

These are Ollama model tag names. If you swap to vLLM, the model identifiers change (vLLM uses HuggingFace model paths like `google/gemma-4-26b`). The oven abstraction cleanly separates the API layer (`ollama.py`), but the role mapping is coupled to Ollama's naming convention at the config layer.

This is a small thing now, but it's the kind of leak that grows. The fix is straightforward (abstract model identity from model name), but it's worth noting because the design explicitly calls out the oven abstraction as a principle.

### 6. Adaptive Routing Has a Cold Start Problem

The design envisions the Innkeeper reading the ledger before making routing decisions. But:

- The ledger needs historical data to be useful
- Historical data requires running tasks through the pipeline
- Running tasks requires routing decisions
- Routing decisions need... the ledger

The multi-armed bandit framing is correct, but the exploration strategy isn't specified. How many tasks go to the "wrong" cook before the ledger has enough signal? What's the default routing when the ledger is empty? The design says "read the stats files," but doesn't address what happens when there are no stats files.

### 7. GPU Contention Is the Real Constraint, and It's Unaddressed

The RTX 4090 has 24GB VRAM. The Line Cook (gemma4:26b) likely uses most of it. The "Parallel Kitchen" section acknowledges this but offers no solution beyond "GPU contention management."

In practice, this means:
- Only one GPU-backed model runs at a time
- The Scout (CPU) and Line Cook (GPU) can run in parallel, but two Line Cook instances cannot
- Model swapping (unload gemma4:26b, load gemma4:31b for Head Chef escalation) takes real time

The design's escalation chain (Line Cook -> Head Chef -> Owner Cooks) implies the Head Chef runs locally on GPU. But loading a different model means unloading the Line Cook. If the Line Cook is handling another order, you can't escalate without blocking it.

**The question the design needs to answer:** Is the GPU a single-threaded bottleneck, or can models be time-shared? If single-threaded, the "parallel kitchen" is really "parallel prep + sequential cooking," and the Innkeeper is actually a scheduler, not just a classifier.

### 8. Context Accumulation Cost Is Unquantified

The Scribe Problem is correctly identified: the Innkeeper accumulates context across all stages. But the design doesn't address the token cost of this accumulation.

If the Innkeeper sees every stage's full output, its context window grows with every step. For a complex task with scout, prep, cook, cleanup, review, feedback, re-cook, re-review, the Innkeeper might be carrying 50K+ tokens of accumulated context. At Opus pricing, that's significant.

The alternative (summarize aggressively between stages) loses information that might matter for reclassification. This is a real tension with no clean answer, but the design should at least acknowledge the cost curve.

### 9. The Roadmap Gaps Are Enormous

```
v0.1: One health resource (done)
v0.2: More windows (roster, ledger)
v0.3: Front door (task submission)
v0.4: Kitchen dispatch
v0.5: GitHub integration
v0.6: Ledger analytics
v1.0: Full inn
```

The complexity jump from v0.2 to v0.3 is where the entire orchestration problem lives. "Task submission" means: intake, classification, routing, dispatch, monitoring, feedback handling, result aggregation. That's not one version — that's the whole design document compressed into a single milestone.

Similarly, v0.4 "kitchen dispatch" is the adaptive routing system, the escalation chain, the parallel scheduling, GPU contention — basically everything in the "Hidden Complexity" section.

The roadmap is honest about what's needed but misleading about the effort distribution. v0.1 and v0.2 are window-dressing (read-only resources). v0.3-v0.4 is where the real system gets built, and it's where most of the design's assumptions get tested.

---

## Contradictions Summary

| Claim A | Claim B | Tension |
|---------|---------|---------|
| ~~Innkeeper is the hub of the star topology~~ | ~~Agents live outside the inn container~~ | ~~RESOLVED: Innkeeper is `claude -p` in a container, spouse is systemd on host~~ |
| Expensive model touches few tokens | Every interaction flows through Opus | 5-6 Opus calls per task != "few tokens" |
| The oven is swappable | Role map keys are Ollama tag names | Config layer leaks the abstraction |
| ~~Bard runs as systemd units~~ | ~~Inn runs in Docker~~ | ~~PARTIALLY RESOLVED: spouse is systemd (correct level), Bard stays in Docker~~ |
| 20+ roles in the roster | ~6 are actually agents | Role count overstates system complexity |
| Parallel kitchen with multiple orders | One GPU, one model at a time | Parallelism is prep-only, cooking is sequential |

---

## Recommended Next Steps

1. ~~**Resolve the Innkeeper identity.**~~ RESOLVED — Innkeeper is `claude -p` in a container, spouse is systemd on host. See issue #1.

2. **Separate agents from tools in the taxonomy.** Keep the metaphor, but mark which roles are agents (make decisions, consume tokens) vs. tools (run scripts, cost nothing). The Ledger schema, the event protocol, and the Bard's scope all depend on this distinction.

3. **Sketch the Opus call budget for a single task.** Walk through one "standard" task end-to-end and count every Innkeeper interaction. If it's 5-6 calls, the cost model in the design doc is wrong by 5x.

4. **Acknowledge the GPU scheduling problem explicitly.** It's the primary physical constraint on the system and it shapes what "parallel" actually means.
