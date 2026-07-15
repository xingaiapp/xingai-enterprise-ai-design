---
title: Anthropic's Loop Engineering Primer - Four Loop Types for Agent Work
author: Xing Wang
date: 2026-07-15
tags: [architecture, enterprise, loop-engineering, agents, claude-code, mcp, education, design-patterns]
description: Anthropic published an official Claude Code guide to loop engineering on 2026-06-30. This article walks through their definition of a loop, the four loop types, verification and token-cost rules — and how they fit XingAI's Prompt → MCP → Loop timeline for agent tutorials.
---

# Anthropic's Loop Engineering Primer: Four Loop Types for Agent Work

On **2026-06-30**, the Claude Code team published [Loop engineering: Getting started with loops](https://claude.com/blog/getting-started-with-loops). It is one of the clearest *vendor* definitions of **loop engineering** we have so far: not a new research paper, but a practical taxonomy from a team running agents every day.

XingAI already framed enterprise AI as a runtime / loop problem in [Beyond Prompt Engineering](2026-07-03-beyond-prompt-engineering-loop-engineering.md) and [From Prompt to Loop](2026-07-03-prompt-to-loop-ai-native-architecture.md). This post is the companion reading note: what Anthropic said, what it means for agent / MCP tutorials, and where it belongs in the engineering timeline.

> Source of record: Delba de Oliveira & Michael Segner, *[Loop engineering: Getting started with loops](https://claude.com/blog/getting-started-with-loops)*, Claude / Anthropic, 2026-06-30. The interpretations below are XingAI's.

---

## Why this article matters

For a few years the public ladder looked like this:

```text
Prompt Engineering
        │
        ▼
Context Engineering
        │
        ▼
Agent Engineering
```

Claude Code's framing pushes a different design object:

```text
Loop Engineering
```

Their claim is blunt: **what you need to design is not primarily the prompt — it is the loop the agent keeps running until a stop condition fires.**

That matches what XingAI calls Loop Engineering on the platform side. Anthropic's post gives the coding-agent-native vocabulary for the same idea: triggers, stop conditions, verification skills, and when *not* to use a heavy loop.

---

## Anthropic's definition of a loop

Officially (paraphrased from the post):

> **A loop is an agent repeating cycles of work until a stop condition is met.**

In practice:

```text
Goal
   │
   ▼
Plan
   │
   ▼
Execute
   │
   ▼
Verify
   │
   ▼
Need more work?
   │
  Yes ──────────────┐
   │                │
   ▼                │
 Iterate ───────────┘
   │
  Done
```

If that diagram feels familiar, it should: it is a production-shaped cousin of **ReAct** (reason → act → observe → repeat), with explicit **stop criteria** and a stronger emphasis on **external verification**.

---

## Four loop types

Anthropic sorts loops by trigger, stop condition, and job shape:

| Type | Trigger | Stop | Best for |
| --- | --- | --- | --- |
| **Turn-based** | User prompt | Agent decides done (or needs more context) | Short, one-off tasks |
| **Goal-based** | User-defined goal (`/goal`) | Goal met **or** turn cap | Verifiable work (tests, scores, CI) |
| **Time-based** | Timer (`/loop`, `/schedule`) | Cancelled, or the external work finishes | Recurring ops: PR watch, morning briefing |
| **Proactive** | Event / schedule, no human in the room | Each task exits on its goal; the routine runs until you turn it off | Streams of defined work (bugs, triage, upgrades) |

### 1. Turn-based loop

Classic chat / tools path:

```text
User → LLM → Tool → LLM → Return
```

You still close the outer loop. Every "did it actually work?" check that you keep in your head stays in your head — until you encode it as a **skill** so the agent can verify more of its own work before handing back.

### 2. Goal-based loop (`/goal`)

Example from Anthropic:

```text
/goal get the homepage Lighthouse score to 90 or above, stop after 5 tries.
```

The agent runs, measures, fails the bar, retries, until either the goal holds or the try budget is spent.

The important design rule: **done is judged against an explicit criterion (ideally by an evaluator), not by the same model quietly declaring "looks good."** Deterministic checks — tests passed, score thresholds, CI green — beat vibes.

That is already agent-engineering best practice. `/goal` just makes the stop condition a first-class primitive.

### 3. Time-based loop (`/loop` / `/schedule`)

Example:

```text
/loop 5m check my PR, address review comments, and fix failing CI
```

Or a morning Slack summary → daily brief. Same work shape, new inputs each tick. Local `/loop` dies when the machine sleeps; cloud `/schedule` moves the tick off your laptop.

### 4. Proactive loop

Compose schedule + goal + verification + optional multi-agent review into a routine that keeps going without a human turn for each item. Anthropic's bug-report example: every hour, find new reports, triage / fix / review / reply, with auto mode so the routine does not stop to ask permission on every step.

That is the shape people mean when they say **autonomous agent** — and the place where governance, audit, and cost control stop being optional.

---

## Design principles Anthropic emphasizes

Quality of loop output depends on the *system around* the loop:

1. **Keep the codebase clean** — agents copy whatever conventions already exist.
2. **Verification skills** — encode "done" so the agent can measure, not perform.
3. **Fresh-context reviewer** — a second agent (or `/code-review`) that did not write the change.
4. **Fix the system, not only the instance** — when a run fails a standard, promote the lesson into docs / skills / checks for the next run.

XingAI's version of the same stack:

```text
Prompt / intent
        │
        ▼
Loop (trigger + stop)
        │
        ▼
Verification (skills, tests, ledgers)
        │
        ▼
Tools / MCP
        │
        ▼
Reviewer / human gates (when risk is high)
        │
        ▼
Repeat or exit
```

---

## Token and cost control

Anthropic's cost advice is unsurprising and still ignored in demos:

- Not every task needs a rich loop — start with the simplest type that works.
- Write **clear goals and hard stop criteria** so the agent cannot wander forever.
- **Pilot** before spawning large dynamic workflows.
- Prefer **scripts for deterministic work**; do not burn tokens re-deriving a form-filler every time.
- Do not schedule more often than the watched system actually changes.
- Use usage tooling (`/usage`, `/goal` status, workflow token views) and kill runaway agents.

For XingAI products: decide **which loop type** a feature is before you wire MCP tools. A decision cache worker that refreshes on a schedule is a *time-based* loop with a hard budget. A chat analyze button is *turn-based*. Mixing them without naming the stop condition is how token bills and silent wrong answers happen.

---

## Where this belongs in an AI Agent / MCP tutorial

Suggested reading timeline:

| Year | Work | Contribution |
| --- | --- | --- |
| 2022 | [ReAct](https://arxiv.org/abs/2210.03629) | Reason + Act loop |
| 2023–2025 | OpenAI function calling / Anthropic tool use | Tool-call mechanism |
| 2025–2026 | [MCP specification](https://modelcontextprotocol.io/specification) | Standard tool / context protocol |
| 2026 | [Building Effective AI Agents](https://www.anthropic.com/engineering/building-effective-agents) | Workflow vs agent |
| **2026-06-30** | **[Getting started with loops](https://claude.com/blog/getting-started-with-loops)** | **Vendor loop taxonomy (Claude Code)** |
| 2026-07 | XingAI Loop Engineering articles | Enterprise runtime / platform framing |

The progression your tutorial can teach:

```text
Prompt Engineering
        │
        ▼
Function Calling / Tool Use
        │
        ▼
ReAct
        │
        ▼
Agent (turn-based)
        │
        ▼
MCP (tool boundary)
        │
        ▼
Loop Engineering (goal / time / proactive)
        │
        ▼
Autonomous Agent OS (with gates, audit, cost)
```

Put **Anthropic's four types** in the **Agent Loop** chapter. Put **XingAI's** earlier posts next to them for enterprise runtime, decision ledger, and Invest decision-cache boundaries — the Claude Code guide is coding-agent-native; XingAI's articles are product- and platform-native.

Also keep this link in [`docs/xingai-engineer-learning-resources.md`](../docs/xingai-engineer-learning-resources.md).

---

## Closing

Anthropic did not invent looping agents in June 2026. What they did publish is a **shareable taxonomy** with stop conditions, verification, and cost rules you can teach without hand-waving.

If you only remember one line from their post: **design the loop and the stop condition; the prompt is just how a turn starts.**

---

## References

- Delba de Oliveira & Michael Segner, [Loop engineering: Getting started with loops](https://claude.com/blog/getting-started-with-loops), Anthropic / Claude, 2026-06-30
- Yao et al., [ReAct: Synergizing Reasoning and Acting in Language Models](https://arxiv.org/abs/2210.03629), 2022
- Anthropic, [Building Effective AI Agents](https://www.anthropic.com/engineering/building-effective-agents)
- Model Context Protocol, [Specification](https://modelcontextprotocol.io/specification)
- Xing Wang, [Beyond Prompt Engineering: Why Enterprise AI Is a Runtime Problem](2026-07-03-beyond-prompt-engineering-loop-engineering.md)
- Xing Wang, [From Prompt to Loop: AI-Native Architecture Evolution](2026-07-03-prompt-to-loop-ai-native-architecture.md)

## Disclaimer

Educational summary for XingAI engineers and tutorial authors. Not legal, compliance, or Anthropic product advice. Always prefer the [original Anthropic post](https://claude.com/blog/getting-started-with-loops) for CLI flags and product features; primitives such as `/goal`, `/loop`, and `/schedule` may change.
