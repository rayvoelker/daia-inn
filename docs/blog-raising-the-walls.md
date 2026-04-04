# Raising the Walls: Building the Watchman with Two Agents and a Phone

The inn has walls now. Not all of them, but the first three rooms are framed and the tests are passing.

This is the story of how v0.1 — The Watchman — went from a design spec to working code, built by a pair of Claude sessions running in tmux on daia while I watched from my phone.

## The Setup

Two Claude sessions, split-paned in a single tmux window. The top pane is the **foreman** — an Opus session executing a 7-task implementation plan using subagent-driven development. It dispatches Sonnet agents for each module, TDD-style: write failing tests, implement until green, commit, move on.

The bottom pane is the **overseer** — another Opus session connected via remote control, acting as a second pair of eyes. It can peek at the foreman's pane, check git status, run the test suite, and report back. A foreman who builds and a manager who walks the floor.

I'm on my phone. The tmux session is on daia. Remote control means I can interact through the web UI without squinting at a terminal on a 6-inch screen.

## What Got Built

Three modules, fifteen tests, all green in 0.01 seconds:

**`src/config.py`** — The inn's settings. Ollama URL, server port, meminfo path, and the role map that tells the inn which model fills which role. Everything overridable via environment variables, because this runs in Docker and containers don't have config files — they have env vars.

```python
ROLE_MAP: dict[str, str] = {
    "gemma4:26b": "line_cook",
    "gemma4:e4b-cpu": "scout",
    "gemma4:e4b": "scout_gpu",
    "gemma4:31b": "head_chef",
}
```

Three tests: defaults load correctly, env vars override them, and the role map resolves models to inn roles.

**`src/system.py`** — The inn's eyes on the hardware. Parses `nvidia-smi` CSV output into a `GpuStats` dataclass (name, VRAM used/total, utilization percentage) and `/proc/meminfo` into `RamStats`. Pure functions for parsing, thin async wrappers for the actual shell calls and file reads.

Four tests: normal nvidia-smi output, empty output, normal meminfo, empty meminfo.

**`src/health.py`** — The watchman's report. Takes the raw data from the other two modules — Ollama's `/api/ps` response, its version, GPU stats, RAM stats — and assembles the `inn://health` JSON structure. This is the module that answers the question: *can you see the kitchen? Are the ovens on?*

```python
def build_health_report(
    ollama_ps, ollama_version, gpu, ram, config
) -> dict[str, Any]:
```

Eight tests: parsing two loaded models, empty model list, unknown roles, version extraction, the full report assembly, Ollama-down scenarios, and no-GPU fallback.

## The Interesting Parts

**Separation of parsing from fetching.** Every module follows the same pattern: pure functions that parse strings or dicts into typed dataclasses, tested without mocking anything. The actual I/O — HTTP calls to Ollama, subprocess calls to nvidia-smi, file reads from /proc — lives in thin async wrappers that are almost too boring to test. The business logic is trivially testable. The I/O layer is trivially inspectable.

**The role map is the architecture.** The config module doesn't just store settings — it encodes the inn's staffing decisions. `gemma4:26b` is the line cook because it's the 26-billion-parameter model that fits in VRAM and runs at 50 tokens/second. `gemma4:e4b-cpu` is the scout because it's the smaller model that runs on CPU when the GPU is busy. When the health report says "line_cook: loaded, GPU," that's not a label — it's a statement about what the inn can serve right now.

**The foreman stalled once.** About 37 minutes into Task 2 (system stats), the dispatched Sonnet agent stopped making progress. The timer kept climbing but tokens stopped flowing — likely a dropped API connection. The overseer caught it by comparing successive snapshots of the tmux pane. Same output, same token count, spinner still alive but nothing happening. A restart fixed it, and the foreman picked up cleanly from where it left off.

This is the value of the two-pane setup. A single agent running alone would have sat there burning wall-clock time with no one watching. The overseer saw it stall, flagged it, and I bounced it from my phone. Total downtime: the time it took me to read the message and hit a button.

## What's Left

The foreman was working on **Task 5: MCP Server Entry Point** when I pulled this snapshot — the module that registers `inn://health` as an MCP resource and wires everything together. After that: Docker setup (Task 6) and an integration smoke test (Task 7).

Then The Watchman is done. One MCP resource, one window into the inn. You connect a client, read `inn://health`, and you can see:

- Is Ollama running? What version?
- Which models are loaded? What roles do they fill?
- How much VRAM is in use? How much RAM?
- Is the kitchen ready to cook?

It's not much. It's exactly enough.

## The Process Observation

I didn't write any of this code. I didn't review any of it until after it was committed. I watched two AI agents coordinate through a terminal multiplexer, checked in periodically from a phone, caught one stall, and kicked it back into motion.

The foreman made every implementation decision — TDD cycle, module boundaries, what to parse and how. The overseer made every operational decision — is it stuck? are the tests passing? is everything committed? The human (me) made one decision: restart the stalled agent.

Three actors, three roles, zero ambiguity about who does what. That's the inn model in miniature. And it built itself.

---

*Fifteen tests. Three modules. Two agents. One phone.*

*The walls are up. Time to hang the door.*

---

Previously:
- [The Handoff](blog-the-handoff.md) — how a link aggregator became a workstation
- [It's Markdown All the Way Down](blog-claude-code-agents.md) — how the pipeline works
- [The Inn Model](blog-the-inn-model.md) — the full role taxonomy and economics
- [daia-inn v0.1 Design Spec](daia-inn-v01-design.md) — The Watchman
