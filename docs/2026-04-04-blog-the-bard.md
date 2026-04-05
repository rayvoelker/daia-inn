---
title: "The Bard"
subtitle: "Who Watches the Workers?"
date: 2026-04-04
series: daia-inn
order: 6
---

# The Bard: Who Watches the Workers?

Yesterday I watched a Claude session die.

Not crash — die. The process was running. The spinner was spinning. The token counter had stopped climbing twenty minutes ago, but nothing in the UI told me that. The agent was a corpse with a pulse, and no one in the pipeline noticed except me, squinting at a tmux pane from my phone.

I bounced it, the foreman recovered, the walls went up. But the question stuck: **who notices when a worker dies?**

## The Genealogist

I went looking for the answer in the inn model, and I found it in a Wikipedia article about bards.

Here's what I thought bards did: sing songs, tell stories, entertain the court. Here's what they actually did: **maintained the genealogy of the ruling family, wrote elegies for the dead, and performed at every opening and closing of court.** They were the institutional memory with a voice. The reason a Celtic court knew its own history, laws, and lineage.

The bard didn't rule. The bard *informed* the ruler. And the bard was the one who stood up and declared, publicly, that someone was gone.

That's the missing role in the inn.

## Two Ways to Know Things

The Bard has two input channels, and the distinction matters.

**Channel one: independent observation.** A systemd timer, running outside the pipeline, taking the pulse of every active worker. Is the line cook still producing tokens? Is the scout still writing output? This has to be independent — you can't ask the Innkeeper to monitor itself. The overseer in my tmux setup was doing exactly this: comparing successive snapshots of the pane, looking for change. Same output twice means the worker is gone.

**Channel two: events from the Innkeeper.** After each pipeline stage, the Innkeeper fires a structured event — "scout finished," "cook dispatched," "cook died, escalating." The Bard assembles these into the genealogy of the task. Born, scouted, handed off, died, reborn, completed, shipped. The full lineage.

If the Innkeeper dies mid-task, the genealogy has a gap. The last known event plus silence is itself a signal. A missing elegy is an elegy.

## The Elegy

When the Bard detects a death, it writes a structured record:

```yaml
elegy:
  worker: coder (gemma4:26b)
  task: "add URL validator"
  died_at: beat 3 of 5
  last_output: "implementing test_normalize..."
  cause: "no token output for 120s"
  inn_version: ac67ad5
```

Then it tells the Innkeeper: *the line cook is dead.*

The Innkeeper decides what to do — restart, escalate, reassign. The Bard never acts on its own observations. It informs. The ruler rules. The bard records.

## Opening and Closing Court

The other thing real bards did: they performed at the opening of every court session and the closing. The ceremony that said "we are now in session" and "we are now adjourned."

The Bard opens the inn. At startup, it reads the Watchman's health report, records the state — git SHA, model roster, GPU and RAM — and starts the heartbeat timers. The opening verse.

The Bard closes the inn. At shutdown, it stops timers, writes a session summary — uptime, tasks served, escalation rate, final state — and seals the record. The closing verse.

Every session is bookended. If you find an opening verse without a closing verse, something went wrong. The absence of the elegy tells the story.

## The Farmer at the Gate

While I was pulling on the Bard thread, two other roles clarified themselves.

The **Farmer** doesn't grow crops in the traditional sense — no planting, no harvesting. The Farmer watches the market. New model dropped on Ollama? New quantization of an existing family? The Farmer tracks what's available, compares it against the current roster, and presents candidates to the Innkeeper.

"There's a new gemma4:34b this season. Claims 45 tok/s on a 4090. Want me to have the Carter bring some in?"

The Farmer scouts the market. The Carter fetches. The existing benchmark test suite — 16 tests across 5 categories — runs the trial. The Innkeeper decides whether to promote. Four roles, clean handoffs, no overlap.

And the Carter got an upgrade: **inspection.** A real carter wouldn't haul spoiled meat back to the inn. The Carter now scans what it fetches before bringing it inside the walls. Virus scans, checksum verification, integrity checks. Fetch and inspect, one role, until the security work gets complex enough to split off into its own role — the Assayer, the one who bites the coin to check if it's gold.

## The Scribe's New Stamp

One more small addition that turns out to be load-bearing: **the inn's own version in every ledger entry.**

The Scribe already writes the receipt — commit message, PR description, final stats. Now it also stamps every record with the inn's git SHA. Which means you can answer questions like:

- "Performance dropped this week — what changed in the inn?"
- "This model worked better under v0.1.2 than v0.1.3 — why?"
- "Did the new routing logic actually help?"

Without the stamp, you can track model performance but you can't track the inn's own evolution. With it, the inn becomes observable to itself.

## The Pattern

Every time I go deeper into the inn model, the same thing happens: a gap in the pipeline maps to a historical role that already has a name, a job description, and clear boundaries.

Who watches the workers? The Bard.
Who scouts the market? The Farmer.
Who inspects the goods? The Carter.
Who stamps the receipt? The Scribe.

These aren't metaphors bolted onto software concepts. They're job descriptions that existed for centuries because the problems they solve are fundamental. Someone has to watch the workers. Someone has to know what's available at market. Someone has to check the goods. Someone has to keep the books.

The inn model keeps revealing roles I didn't know I needed, and every one of them maps to a real gap in the pipeline. I'm starting to think the metaphor isn't a metaphor. It's a taxonomy that medieval innkeepers figured out through centuries of operational experience.

We're just rediscovering it with GPUs.

---

*The bard watches the workers, keeps the genealogy of every task, and tells the innkeeper when someone has died. That's the job. It always was.*

---

Previously:
- [Raising the Walls](2026-04-04-blog-raising-the-walls.md) — building the Watchman with two agents and a phone
- [The Handoff](2026-04-03-blog-the-handoff.md) — how a link aggregator became a workstation
- [The Inn Model](2026-04-03-blog-the-inn-model.md) — the full role taxonomy and economics
- [It's Markdown All the Way Down](2026-04-03-blog-claude-code-agents.md) — how the pipeline works
