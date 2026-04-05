# The Kitchen Opens

## What a Running Inn Actually Looks Like

I keep getting asked the same question: "So what does this thing actually *do*?"

Fair. The inn model describes 25 roles, three cost tiers, a star topology, and a supervisor pattern from Erlang. But what does it look like when someone walks through the front door?

## A Typical Order

You're building munews.app. You need a URL normalizer — strip tracking parameters, normalize protocols, handle the edge cases. You open Claude Code on your laptop and type one sentence:

> "Add a URL normalizer to munews — strip tracking params, normalize protocol, handle edge cases."

Here's what happens next.

Your Claude Code session connects to the inn over Tailscale and reads the serving window. `inn://health` says the oven is hot and the Line Cook is loaded. `inn://roster` says the Line Cook handles utility tasks at 95% first-try success. `inn://ledger` says similar tasks took 3-5 minutes.

Your session calls `inn.dispatch()`. A fresh Innkeeper container spins up — `claude -p` with an API key and a markdown file that contains the entire inn model. The Innkeeper reads the ledger, classifies this as STANDARD, and starts orchestrating.

First, the Scout. The small model on CPU explores the codebase, finds the existing utils directory, identifies test conventions, reports back. Takes about 30 seconds.

The Innkeeper writes a test spec — twelve tests across three edge case groups. Then dispatches the Line Cook with the tests and the Scout's findings.

The Line Cook — gemma4:26b running on the 4090 at 50 tokens per second — starts the TDD loop. Read the tests, write code, run the tests. Ten of twelve pass on the first try. It fixes the other two. All green in about four minutes.

The Chambermaid runs a cleanup pass. Removes one unused import, sorts the rest. No semantic changes — ever. If `ruff` wouldn't do it, neither does she.

The Waitstaff reviews. Sonnet looks at the diff, flags one design suggestion for the backlog, approves. The Scribe writes a commit message and a PR description, records everything to the ledger: who cooked, how many attempts, what it cost.

The Innkeeper exits. Your Claude Code session gets back a PR URL.

Total wall time: six minutes. Total cost: about twelve cents — Opus for classification, Sonnet for review, everything else free or fractions of a cent. Your involvement: one sentence.

## The Multiplier

One task is nice. Ten tasks before lunch is the point.

```
"Add URL normalizer"          → Line Cook     4 min   $0.12
"Fix date parser timezone"    → Line Cook     3 min   $0.10
"Rename config module"        → Kitchen Boy   30 sec  $0.01
"Add rate limiter middleware"  → Head Chef     8 min   $0.15
"Update dependencies"         → Farrier       5 min   $0.03
```

Five tasks, twenty minutes of wall time, forty-one cents. You review five PRs over coffee.

The GPU is the bottleneck — one model loaded at a time on the 4090. But prep and cleanup run on CPU. The Scout explores while the Line Cook is finishing the previous order. The Chambermaid and Scribe clean up while the next order is being prepped. The Innkeeper schedules around the constraint. That's why it's a scheduler, not just a classifier.

## What the Inn Is Good At

The sweet spot is tasks where the judgment is in the classification, not the execution. The Innkeeper spends expensive tokens deciding what to do. The Line Cook spends zero-cost tokens doing it.

This works well for:

- **Utility functions** — validators, parsers, formatters, slugifiers
- **Bug fixes** with clear reproduction steps and test cases
- **Pattern-following features** — new endpoints that mirror existing ones, new modules that follow established conventions
- **Mechanical refactors** — renames, extractions, interface changes with known scope
- **Dependency maintenance** — updates, security patches, version bumps with test suites to verify

What it's not good at — yet:

- **Greenfield architecture** — no patterns to follow, no ledger history to consult
- **Ambiguous requirements** — "make it better" needs human judgment, not routing
- **Long reasoning chains** — tasks that require understanding 20 files at once push context limits
- **UI and design work** — models are weak here regardless of orchestration

The ledger changes the boundary over time. As the inn handles more tasks, the Innkeeper gets better at classifying. Tasks that needed the Head Chef last month might go straight to the Line Cook this month. The multi-armed bandit converges.

## Running Autonomously

Here's the question that makes people nervous: can this run on its own?

Yes. And the design has specific controls for that. The inn isn't autonomous the way a rogue agent is autonomous. It's autonomous the way a well-run kitchen is autonomous — clear authority hierarchy, budget enforcement, circuit breakers at every level.

### The Authority Stack

```
┌─ Human ─────────────────────────────────────┐
│  Reviews PRs. Approves merges. Sets budget.  │
│  Can shut everything down at any time.       │
├─ Spouse (systemd) ──────────────────────────┤
│  Watches the Innkeeper. Kills on stall.      │
│  Enforces per-task budget. Enforces timeout. │
│  The only thing outside Docker.              │
├─ Innkeeper (claude -p in Docker) ───────────┤
│  Classifies. Routes. Reclassifies on fail.   │
│  Per-task lifecycle — exits when done.        │
│  Reads ledger before every decision.         │
├─ Inn (MCP server in Docker) ────────────────┤
│  Serves resources. Executes tools.            │
│  No decisions. No autonomy.                  │
├─ Oven (Ollama in Docker) ───────────────────┤
│  Runs prompts. Returns tokens.               │
│  Doesn't know what it's being used for.      │
└─────────────────────────────────────────────┘
```

Every layer has a kill switch held by the layer above it. The oven can't decide to cook. The inn can't decide to serve. The Innkeeper can't decide to overspend. The spouse kills the Innkeeper if it stalls. The human reviews every PR before it merges.

### Budget as a Circuit Breaker

The Innkeeper runs per-task with a budget ceiling. The spouse enforces it:

- Task budget exceeded → spouse kills the Innkeeper, logs the overspend
- Session budget exceeded → spouse stops starting new tasks
- No output for 120 seconds → spouse kills and restarts
- Task duration exceeds ledger average by 3x → spouse sends a warning, then kills

The Innkeeper never sees its own budget constraint. The spouse enforces it from outside. You can't negotiate with your supervisor if your supervisor is a bash script.

### The PR Gate

Nothing merges without human review. The inn produces PRs, not merged code. The Scribe writes the description, the tests are green, the Waitstaff approved — but the final merge is a human action.

This is the critical constraint. The inn is autonomous in *production* but gated in *delivery*. It can cook all day. It can't serve a dish the owner hasn't tasted.

### Network Isolation

The inn runs on a single workstation behind Tailscale. No public endpoints. The Innkeeper can reach the Anthropic API (outbound) and the inn's MCP server (internal). It cannot reach the internet, other machines, or services outside the tailnet. The oven has no network access at all — it runs prompts, nothing else.

Docker provides container isolation. The Innkeeper can't modify the inn's code. The inn can't modify the oven's models. Each container has only the capabilities it needs.

### What "Autonomous" Actually Means

The inn can:
- Accept tasks from a queue
- Classify and route them without human input
- Run the full pipeline (scout, prep, cook, clean, review, scribe)
- Produce PRs and ledger entries
- Operate 24/7 with the spouse watching for failures

The inn cannot:
- Merge its own PRs
- Modify its own code or configuration
- Access systems outside the tailnet
- Exceed its budget
- Run longer than the spouse allows
- Decide to do something it wasn't asked to do

This is the difference between autonomy and agency. The inn has autonomy within its operational boundary. It doesn't have agency — it doesn't choose its own goals. Tasks come from outside. The inn processes them. The human decides what to do with the output.

### The Night Shift

The real payoff of autonomous operation is overnight work. You queue up the day's backlog before bed:

```
Queue:
  - 3 bug fixes from today's triage
  - 2 utility functions for the new module
  - 1 dependency update (security patch)
  - 1 documentation pass on the API module
```

The inn processes them sequentially (one GPU). The spouse watches for stalls. Each task produces a PR with green tests. You wake up to seven PRs in your inbox, a ledger showing what worked and what escalated, and a total cost under two dollars.

If something failed — the Line Cook got stuck, the tests didn't pass, the Head Chef couldn't resolve it — the ledger tells you exactly where and why. The Bard's genealogy shows the full task lineage. Nothing is hidden.

That's what the kitchen opening looks like. Not a single brilliant agent doing everything. A well-staffed inn where each role does one thing, the expensive model only touches decisions, and a bash script on the host makes sure nobody works past their shift.

---

*The inn runs itself. The owner checks in each morning, reviews what shipped, reads the ledger, and decides what to cook next. The rest is kitchen work.*
