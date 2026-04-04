---
title: "It's Markdown All the Way Down"
subtitle: "How Claude Code Turns Prose Into a Development Pipeline"
date: 2026-04-03
series: daia-inn
order: 1
---

# It's Markdown All the Way Down: How Claude Code Turns Prose Into a Development Pipeline

I've been building a multi-model agent pipeline on a library workstation with an RTX 4090, and somewhere around hour forty I had the realization that changed how I think about AI-assisted development: **there is no framework**.

## The Setup

I'm building [munews.app](https://munews.app), an AT Protocol link aggregator. The architecture is a Rust microkernel — capability-enforced modules, server-rendered HTML, SQLite, the whole thing. But this post isn't about the app. It's about how I accidentally built a software development factory out of markdown files and a command-line tool.

Here's what my pipeline looks like:

```
Me (human)
  → orchestrator (Opus, cloud, $$$)     writes tests, makes decisions
      → scout (gemma4:e4b, local, free)  explores the codebase
      → coder (gemma4:26b, local, free)  implements until tests pass
      → reviewer (Sonnet, cloud, $$)     code review, auto-fixes
```

The orchestrator writes the tests — the contract — then dispatches a local model running on my GPU to implement until those tests pass. If the local model gets stuck, it escalates to a cloud model. If that fails, the orchestrator (the most expensive model) implements it directly as a last resort.

The first time I ran it for real, the local 26B parameter model passed all 27 tests on its first attempt in 25 seconds. Zero escalations. The expensive cloud model only spent tokens on the high-judgment work: designing the tests and verifying the results.

That felt like something.

## The Part That Broke My Brain

Here's the orchestrator agent definition. The entire thing:

```markdown
---
name: orchestrator
model: opus
---

You are the tech lead of a multi-model development pipeline.
You write the tests, dispatch agents to implement, and verify
the results. You never write implementation code yourself
unless all other agents have failed.

## Pipeline Process

1. Dispatch scout to explore relevant codebase areas
2. Write failing tests that define the acceptance criteria
3. Dispatch coder with the test file and failure output
4. Review coder's report — if BLOCKED, escalate
5. Dispatch reviewer for code review
6. Run final verification, write stats, commit
```

That's it. That's the workflow engine. There's no DAG, no state machine, no YAML pipeline definition, no framework. The orchestrator is a markdown file that tells a language model how to be a tech lead. When I run:

```bash
claude --agent orchestrator "Add a slugify utility"
```

Claude Code reads that markdown file, becomes the orchestrator, and follows the instructions. When it says "dispatch scout," it spawns another `claude` CLI process with the scout's markdown personality. When that returns, it spawns another for the coder. And so on.

**The workflow is English prose. The execution engine is a language model. The deployment mechanism is a markdown file in a directory.**

I kept looking for the "real" orchestration layer underneath. There isn't one. It's processes spawning processes, each one reading a markdown file that tells it who to be.

## Why the CLI Is the Whole Thing

This only works because Claude Code is a command-line tool. A web chat can't read your files, run your tests, execute git commands, or spawn subprocesses. The CLI can do all of those things, which means it can invoke *itself* as a building block.

Each agent in the pipeline is just a CLI invocation:

```bash
# These are all the same tool, with different instructions
claude --agent orchestrator "Add feature X"    # Opus, writes tests
claude --agent scout "explore src/"            # local 4B, read-only
claude --agent coder "make tests pass"         # local 26B, implements
claude --agent reviewer "review this diff"     # Sonnet, reviews
```

Same binary. Different markdown file. Different model. Different tool permissions. The orchestrator dispatches agents through Claude Code's built-in Agent tool — which spawns a child process with its own context, tools, and instructions. The child runs, returns its results, and the orchestrator decides what to do next. Turtles all the way down.

## The Economics Are the Architecture

The pipeline isn't just a workflow preference. It's an economic architecture.

Opus (the orchestrator) costs real money per token. It's the most capable model — best at judgment calls, test design, knowing when something is wrong. Using it to grind through implementation loops would be like hiring a principal engineer to type boilerplate.

The local 26B model on my GPU costs nothing per token. It runs at 50 tokens/second and passed 16 out of 16 benchmarks I threw at it. It's not as smart as Opus, but it's smart enough to read a failing test and write the code that makes it pass. That's the only job it has.

The pipeline exploits this gap:

| Role | Model | Cost | Speed | Job |
|------|-------|------|-------|-----|
| Orchestrator | Opus (cloud) | $$$ | — | High-judgment decisions |
| Scout | gemma4:e4b (local, CPU) | Free | 13 tok/s | Fast codebase exploration |
| Coder | gemma4:26b (local, GPU) | Free | 50 tok/s | Implementation grinding |
| Reviewer | Sonnet (cloud) | $$ | — | Code review, style fixes |

The expensive model touches as few tokens as possible. The free model does the heavy lifting. The medium-cost model handles review. Cloud costs stay low, but quality stays high because the tests (written by the best model) are the contract that everything else must satisfy.

## What Portability Actually Looks Like

After getting this working, I wanted to reuse the same pipeline on other projects. This led me down the Claude Code plugin system, which taught me something about where the boundaries actually are.

Claude Code has three layers of configuration:

**Global** (`~/.claude/plugins/`) — plugins with skills, commands, and helpers that work in every project. These are things like "how to bootstrap a new repo" or "how to check if my local models are healthy."

**Project** (`.claude/agents/` and `CLAUDE.md`) — agent definitions and project configuration that are specific to a repo. The orchestrator lives here because `claude --agent` only looks at project-level agents.

**Runtime** — the model doing the work reads `CLAUDE.md` to find out which models fill which roles on this particular machine.

The portable part isn't the agent files — it's the *pattern*. The orchestrator always says "read the Model Roster from CLAUDE.md." On my workstation with an RTX 4090, the roster says gemma4:26b. On a laptop with no GPU, it would say Sonnet for everything. The workflow stays the same. The models change.

## What I Learned About Agents

After weeks of building this, here's what I actually believe about AI agents:

**Agents are not programs.** They're documents. A well-written markdown file that describes a role, a process, and constraints is the entire implementation. There's no agent SDK, no runtime, no deploy step. You edit a file and the behavior changes next time you invoke it.

**The orchestration problem is a writing problem.** When my pipeline produced bad results, the fix was never "add retry logic" or "implement a state machine." It was "rewrite paragraph three of the orchestrator to be clearer about when to escalate." Debugging a multi-agent system is editing prose.

**Subagents are just processes.** There's no special protocol for agent-to-agent communication. The orchestrator dispatches the coder through the Agent tool, which spawns a child process with its own context. The coder's output is just text that the orchestrator reads. When the child finishes, its results flow back to the parent. Processes spawning processes, markdown instructing markdown.

**Tests are the interface contract.** In a multi-model pipeline, the models have different capabilities and different failure modes. Tests are the one thing that's unambiguous. The orchestrator writes them, the coder satisfies them, the reviewer validates them. Everyone speaks pytest.

**Cost control is architectural.** You don't optimize API costs with caching or batching. You optimize them by giving expensive models less work. The cheapest token is the one you never send to the cloud.

## The Punchline

I started this project to build a link aggregator. I ended up building a development methodology.

The link aggregator has a formal spec, a 10-task implementation plan, 103 seed stories, and a Rust microkernel architecture. It doesn't have any Rust code yet.

But the pipeline that will build it has been validated end-to-end. The local models are benchmarked. The orchestrator has run real tasks. The stats are tracked. The process works.

And the entire thing — the workflow engine, the agent definitions, the orchestration logic, the escalation rules — fits in four markdown files totaling maybe 400 lines.

It's markdown all the way down. And that's the point.

---

*Written from a Cincinnati library workstation with 32 cores, 124GB RAM, and an RTX 4090 that mass hallucination tells us we don't need anymore.*
