---
title: "The Handoff"
subtitle: "How a Link Aggregator Became a Workstation"
date: 2026-04-03
series: daia-inn
order: 3
---

# The Handoff: How a Link Aggregator Became a Workstation

I started building a news aggregator. I ended up designing an inn.

This is the story of how that happened, and why I think it matters.

## The Original Plan

munews.app is an AT Protocol link aggregator. Old stories from Reddit, Digg, BoingBoing — stuff from six months ago or more — resurface when they rhyme with today's zeitgeist. Hacker News for time travelers. Rust microkernel, SQLite, server-rendered HTML, no JavaScript.

I had a spec, a 10-task implementation plan, 103 seed stories, and a full research KB. I had benchmarked five local models and picked the best two. I had a multi-model pipeline where Opus writes tests, a local 26B model implements for free on my GPU, and Sonnet reviews. The pipeline was validated end-to-end.

I hadn't written a single line of Rust.

## The Yak Shave That Wasn't

You know the xkcd about yak shaving — you start trying to do one thing and end up doing seventeen prerequisite things that are increasingly far from the original task? That's what this looked like from the outside. I was supposed to be building a web app. Instead I was:

- Benchmarking local models against each other
- Writing an orchestrator agent in markdown
- Designing a profile system for swapping model configurations
- Building a test harness for evaluating LLM capabilities
- Writing blog posts about how the pipeline works

Classic yak shave. Except none of it was wasted. Every piece I built was infrastructure I needed anyway. And somewhere in the middle of it, the mental model clicked.

## The Click

I was staring at my pipeline — orchestrator, scout, coder, reviewer — and thinking about what else it needed. Not for munews.app specifically. For everything.

Who scaffolds files before the coder starts? Who cleans up lint after? Who writes commit messages? Who checks if Ollama is even running? Who updates dependencies? These aren't munews.app questions. They're questions about any project on this machine.

Then someone showed me a list of jobs at a medieval inn, and every single one mapped to a pipeline task.

The **innkeeper** manages budget and routes orders. That's the orchestrator. The **line cook** does the volume work. That's the local 26B model. The **kitchen boy** does prep work that's beneath the cook. That's Haiku at a tenth of a cent. The **chambermaid** cleans up after. The **scribe** writes the receipts. The **watchman** checks that the building isn't on fire. The **farrier** maintains the horses. The **dung collector** — well, someone has to clean up Docker volumes.

Twenty-plus roles, all mapping to real tasks that real pipelines need.

## The Realization

The inn isn't a metaphor for munews.app. It's a metaphor for the **workstation**.

daia — my workstation — is the inn. It has an RTX 4090 (the kitchen's oven), 124GB RAM (the pantry), Ollama running in Docker (the kitchen equipment), and a Tailscale connection (the road that travelers arrive on).

munews.app is just the first customer who walked through the door.

Any project can be a customer. A well-scoped GitHub issue is a customer placing an order. The innkeeper classifies it, the kitchen cooks it, tests judge it, and a PR comes out the other end. The inn doesn't care what the customer ordered — a Rust microkernel, a Python utility, a config change — it just needs to know how hard the dish is so it can route it to the right cook.

## The Architecture Flip

This changed how I think about the whole setup:

**Before:** I'm building munews.app. The pipeline is a tool I use to build it.

**After:** I'm running an inn. munews.app is the first customer. The inn is the product.

The inn is infrastructure. It lives in its own repo (`daia-inn`), runs alongside Ollama in docker-compose, and exposes itself as an MCP server. Any MCP client — Claude Code on daia, Claude Code on my laptop over Tailscale, a future GitHub Action — can connect and either peer through the windows (what models are loaded? what's cooking?) or submit an order.

The pipeline I built for munews.app? Those agent definitions — orchestrator, coder, scout, reviewer — they're the inn's first staff. The model benchmarks? That's the innkeeper knowing what each cook can handle. The stats files? That's the ledger. It was all inn infrastructure. I just didn't know it yet.

## The Star Topology

The other thing that clicked: the innkeeper isn't the first step in a pipeline. It's the **hub** of a star.

Every interaction flows through the innkeeper. The scout reports to it. It writes the tests. It dispatches the coder. When tests fail, it decides whether to retry, reclassify, rewrite, or escalate. It accumulates context across every stage so the scribe can write a coherent commit message at the end. It reads the ledger before routing new orders.

That's why the innkeeper is Opus — the most expensive model. Not because it does the most work. Because it makes the most decisions. Every fork in the pipeline is a judgment call, and judgment is what you pay for.

The line cook is free. The kitchen boy costs a tenth of a cent. The chambermaid costs a tenth of a cent. The scribe costs a tenth of a cent. Almost the entire pipeline runs on local models or the cheapest cloud tier. The expensive model only touches the high-judgment moments: test design, failure triage, escalation decisions.

The economics ARE the architecture.

## What I'm Actually Building Now

daia-inn v0.1 is called "The Watchman." It's the smallest possible thing: one MCP resource that reports what models are loaded, GPU and RAM usage, and whether Ollama is healthy. Just the window to peer in. Can you see the kitchen? Are the ovens on?

From there:

- v0.2 adds more windows (queue status, ledger summary)
- v0.3 adds the front door (task submission)
- v0.4 connects to the kitchen (dispatches orchestrator on the host)
- v0.5 opens for external customers (GitHub Issues as orders)
- v0.6 adds the ledger (adaptive routing based on historical success)
- v1.0 is the full inn — all roles staffed, adaptive routing, self-monitoring

munews.app — the Rust microkernel, the capability enforcement, the 103 seed stories — is still the first customer. The 10-task implementation plan is still there, ready to be fed through the pipeline. But now when I build it, I'll be building it *through the inn*, and the inn will get better with every dish it serves.

## The Meta-Lesson

I think what happened is that I was building a tool to build a thing, and the tool turned out to be more interesting than the thing.

Not because the thing (munews.app) isn't interesting — it is. AT Protocol, capability enforcement, zeitgeist matching — there's real novelty there. But the *process* of building it revealed something about how AI-assisted development works at the systems level.

Most people use AI assistants as a single tool: one model, one conversation, one task. What I accidentally built is a **staffed operation** — multiple models at different price points, each with a specific role, coordinated by the most capable model, with a feedback loop that makes routing smarter over time.

And the entire thing — the workflow, the agent definitions, the orchestration, the escalation rules — is four markdown files and a CLI tool that can invoke itself.

It's markdown all the way down. It's an inn all the way up.

---

*The inn is open. The ovens are warm. The first customer is at the door.*

*Time to cook.*

---

Previously:
- [It's Markdown All the Way Down](2026-04-03-01-blog-claude-code-agents.md) — how the pipeline works
- [The Inn Model](2026-04-03-02-blog-the-inn-model.md) — the full role taxonomy and economics
- [The Inn Model — Design Document](design-the-inn-model.md) — directed graphs and hidden complexity
- [daia-inn v0.1 Design Spec](daia-inn-v01-design.md) — The Watchman
