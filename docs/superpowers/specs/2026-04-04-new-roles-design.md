# New & Expanded Inn Roles — Design Spec

> Spec date: 2026-04-04. Status: approved design, pending implementation.
> Phase: post-v0.1. These roles build on top of The Watchman and the Ledger.

## Context

The v0.1 inn ("The Watchman") ships a single MCP resource: `inn://health`. The current roster has four active pipeline roles (Innkeeper, Line Cook, Scout, Reviewer) and a handful of implicit infrastructure jobs (health checks, cleanup, dependency management) that aren't formalized.

This spec defines four new or expanded roles that emerged from brainstorming about what the inn needs next. None of these ship in v0.1. They inform the design of the Ledger, the analytics schema, and the pipeline's evolution.

---

## 1. The Bard

### One-Line Summary

The inn's genealogist and timekeeper — watches workers, tracks the lineage of every task, and tells the Innkeeper when someone has died.

### Historical Basis

Celtic bards maintained genealogies, wrote elegies for the dead, performed at the opening and closing of court, and kept the institutional memory of the clan. They didn't rule — they informed the ruler.

### What the Bard Does

**Takes the pulse (heartbeat)**
- Independent systemd timer, runs outside the pipeline
- Periodically checks whether active agents are still producing output (mechanism TBD per environment — tmux pane snapshot comparison, process stdout monitoring, or log tail diffing)
- Must be independent of the Innkeeper — the Innkeeper might be the one who stalled

**Declares death (elegy)**
- When a worker stops responding, the Bard writes a structured death record:

```yaml
elegy:
  worker: coder (gemma4:26b)
  task: "add URL validator"
  died_at: beat 3 of 5
  last_output: "implementing test_normalize..."
  cause: "no token output for 120s"
  inn_version: ac67ad5
```

- Notifies the Innkeeper: "the line cook is dead"
- The Innkeeper decides what to do (restart, escalate, reassign) — the Bard never acts on its own observations

**Keeps the genealogy (task lineage)**
- Receives structured events from the Innkeeper after each pipeline stage:

```
born        → Innkeeper classified as "standard"
scouted     → Scout explored src/, found 3 relevant modules
handed_off  → dispatched to Line Cook (gemma4:26b)
died        → Line Cook stalled at beat 3 (Bard detected via heartbeat)
reborn      → Innkeeper escalated to Head Chef (Sonnet)
completed   → Head Chef finished, 27/27 tests pass
cleaned     → Chambermaid ran formatting pass
shipped     → Scribe wrote commit message
```

- If the Innkeeper dies mid-task, the genealogy has a gap — the last known event plus silence is itself a signal

**Opens and closes the inn (ceremony)**
- At startup: reads `inn://health` from the Watchman, records the opening state (git SHA, model roster, system resources), starts heartbeat timers
- At shutdown: stops timers, writes session summary (uptime, tasks served, escalation rate, final state)
- Every session is bookended — an opening verse and a closing verse

### Two Input Channels

| Channel | What | Mechanism |
|---|---|---|
| Independent observation | Worker liveness (heartbeat, death detection) | systemd timer, runs outside pipeline |
| Events from Innkeeper | Task lineage (stage transitions, escalations) | Innkeeper fires structured events after each stage |

### What the Bard Does NOT Do

- Route tasks (Innkeeper)
- Decide who cooks (Innkeeper)
- Set iteration budgets (Innkeeper, informed by Ledger)
- Shape context per agent (Innkeeper, as the hub)
- Restart or reassign dead workers (Innkeeper)
- Record final task outcomes (Scribe — writes the receipt)
- Monitor hardware/infrastructure health (Watchman — checks the ovens)

### Overlap Resolutions

| Overlap | Resolution |
|---|---|
| Bard heartbeat vs Watchman health checks | Different targets. Watchman checks infrastructure (Ollama up? GPU available?). Bard checks workers (is this agent still producing tokens?). Watchman = "is the oven on?" Bard = "is the cook still breathing?" |
| Bard genealogy vs Scribe records | Different scope. Scribe writes the receipt (commit message, PR, final stats). Bard keeps the saga (full journey including deaths, restarts, escalations). |
| Bard vs Innkeeper | Bard informs, Innkeeper decides. The Bard says "the cook is dead." The Innkeeper says "send it to the head chef." |
| Bard startup vs Watchman | The Watchman is a window (peers in, reports state on demand). The Bard's opening ceremony is a one-time record at session start — it reads the Watchman's report and writes it into the session timeline. |

### Implementation Sketch (Later Phase)

```
# systemd units (or docker-compose equivalent)

bard-open.service     Type=oneshot, runs at inn startup
                      → reads inn://health, records opening state
                      → starts bard-heartbeat.timer

bard-heartbeat.timer  OnUnitActiveSec=30s
                      → checks active agent liveness
                      → writes elegy if death detected
                      → notifies Innkeeper

bard-close.service    Type=oneshot, runs at inn shutdown
                      → stops timers
                      → writes session summary to ledger
```

---

## 2. The Farmer

### One-Line Summary

Model curator — watches the market for new releases, compares specs against the current roster, and presents candidates to the Innkeeper.

### Historical Basis

The farmer supplies the inn with produce. They don't cook — they grow crops and bring the harvest to market. The inn depends on the farmer for the quality of its raw materials.

### What the Farmer Does

- Watches for new model releases (Ollama library, model family updates, new quantizations)
- Compares candidate specs against the current roster (parameter count, VRAM requirements, reported benchmarks)
- Presents candidates to the Innkeeper: "there's a new gemma4:34b — bigger than our 26b, might fit in VRAM, here are the published benchmarks"
- Tracks model families over time — knows which lineages are worth following

### What the Farmer Does NOT Do

- Download or install models (Carter)
- Run benchmarks (the existing test suite in `tests/models/` handles admission trials)
- Decide to swap models into the roster (Innkeeper)
- Monitor currently loaded models (Watchman)

### Relationship to Existing Infrastructure

The benchmark test suite (currently in munews.app, should move to daia-inn) is the inn's **seed trial plot**. The Farmer identifies what's worth planting. The test suite evaluates whether it grows well. The Innkeeper decides whether it joins the menu.

```
Farmer: "new gemma4:34b is available, 34B params, claims 45 tok/s on 4090"
  → Innkeeper: "pull it, run the trials"
  → Carter: pulls the model
  → Test suite: runs 16 benchmarks
  → Results: 15/16 pass, 42 tok/s actual, fits in 24GB VRAM
  → Innkeeper: "promote to line_cook, demote 26b to backup"
  → Scribe: records the roster change with inn git version
```

### Implementation Phase

Later. Requires Ollama library API access or a scraping mechanism. Could start as a manual checklist the Innkeeper consults before trialing new models, then automate.

---

## 3. The Carter (Expanded)

### One-Line Summary

Fetch and inspect — downloads external resources and scans them for safety before bringing them inside the walls.

### Historical Basis

A medieval carter transported goods from market to inn. A good carter inspected the goods before loading — spoiled meat, weevil-infested grain, counterfeit spices don't make it onto the cart.

### What the Carter Does

**Existing duties (unchanged):**
- Downloads dependencies, model weights, API specs, remote configs
- Knows the route to suppliers (URLs, registries, Ollama library)

**New duty — inspection:**
- Scans fetched files for safety before they enter the inn
- Virus scanning, checksum verification, signature validation where applicable
- For model weights: verifies file integrity, checks expected size matches actual
- For dependencies: checks against known vulnerability databases

### Split Criteria

The Carter holds both jobs (fetch + inspect) until one of these triggers a split:
- Inspection logic becomes complex enough to warrant its own test suite
- Non-Carter sources need inspection (user-submitted files, webhook payloads, external API responses)
- The security inspection step needs to run independently of fetching

When split, the inspection role becomes the **Assayer** (the medieval role that tested coins for genuine gold and wine for poison).

### Implementation Phase

Later. The fetch duties already exist implicitly (Ollama pull, pip/uv install). Adding inspection is incremental — start with checksum verification on model pulls, expand from there.

---

## 4. The Scribe (Expanded)

### One-Line Summary

Now records the inn's own git version in every ledger entry, enabling correlation between inn code changes and pipeline performance.

### Existing Duties (Unchanged)

- Writes commit messages
- Writes PR descriptions
- Records final task stats to the Ledger

### New Duty — Inn Version Tracking

Every ledger entry includes:

```yaml
inn_version:
  git_sha: ac67ad5
  git_tag: v0.1.3  # if tagged
  dirty: false      # uncommitted changes?
```

This enables:
- "Did upgrading the routing logic improve first-attempt success rates?"
- "Performance dropped — what changed in the inn since last week?"
- "This model worked better under inn v0.1.2 than v0.1.3 — what changed?"

### Relationship to the Bard

The Scribe writes the **receipt** (what shipped, final stats, inn version). The Bard keeps the **saga** (full task genealogy, deaths, escalations). The Scribe records outcomes. The Bard records the journey.

The Bard also uses the inn version in its opening/closing ceremonies and elegies — but the Scribe is the one who puts it in the Ledger, because the Scribe owns ledger writes for completed tasks.

### Implementation Phase

Near-term. This is a field addition to the analytics schema. Can ship alongside or shortly after the Ledger.

---

## Role Relationship Map

```
                    ┌─────────────────────────────────────┐
                    │           THE INNKEEPER              │
                    │     (decides everything)             │
                    │                                      │
          informs ◄─┤  fires genealogy events ──► Bard    │
                    │  receives Farmer recommendations     │
                    │  dispatches Carter for fetches       │
                    │  Scribe writes final records         │
                    └──┬───────┬───────┬───────┬──────────┘
                       │       │       │       │
                       ▼       ▼       ▼       ▼
                     Bard   Farmer  Carter  Scribe
                       │                      │
                       │ reads                │ writes
                       ▼                      ▼
                   Watchman               Ledger
                  (inn://health)       (task records +
                                       inn version)
```

## Design Principles

1. **Start combined, split later.** The Carter does fetch + inspect until inspection complexity warrants an Assayer. The Bard handles all timing until different cadences need separate services.

2. **Inform, don't decide.** The Bard and Farmer both report to the Innkeeper. Neither makes routing or staffing decisions. The Innkeeper remains the hub of the star topology.

3. **Two input channels for the Bard.** Independent observation for liveness (can't depend on the thing you're monitoring to report its own death). Event-driven from the Innkeeper for narrative (the hub already sees every stage).

4. **Inn version everywhere.** The Scribe puts it in ledger entries. The Bard puts it in session records and elegies. This is the variable that lets you correlate inn changes with pipeline performance.

5. **The benchmark test suite belongs to the inn, not to any customer.** It should move from munews.app to daia-inn. The Farmer identifies candidates, the test suite evaluates them, the Innkeeper decides.

---

*"The bard watches the workers, keeps the genealogy of every task, and tells the innkeeper when someone has died. The farmer watches the market and says what's worth planting. The carter brings it through the gate, inspected. The scribe stamps every receipt with the inn's own seal."*
