---
title: Evidence Engine + Eval Registry — Citation Verification with an EEE Gate
author: Xing Wang
date: 2026-07-26
tags: [architecture, enterprise, evidence, evaluation, eee, worker-cache, governance, citation-verification, design-patterns]
description: How XingAI separates citation verification compute from evaluation storage and CI regression gates using Evidence Engine and an Every-Eval-Ever registry.
---

# Evidence Engine + Eval Registry: Citation Verification with an EEE Gate

Research and claims teams keep asking the same question:

> *If we verify citations with an LLM, where do the scores live — and how do we stop a “good demo run” from silently regressing next week?*

**Short answer:** Put **verification compute** in Evidence Engine (worker owns logic; API reads cache). Put **evaluation records** in Eval Registry (EEE-shaped files + `diff --fail-on-regression`). Do not store scoreboards inside the dashboard or invent a second schema.

![Evidence Engine + Eval Registry — System Design UX](../assets/evidence-engine-eval-registry-system-design-ux.png)

---

## 5W Framework

### What (What is this about?)

Two repos, one verification → evaluation loop:

| Layer / Component | Role | Orchestrates / Owns |
|---|---|---|
| **evidence-worker** | Ingest markdown/URL, extract claims, check sources, optional LLM support checks, metrics | All compute (Principle 1) |
| **SQLite cache** | Cross-process handoff for dashboard/API | Keys `v1:verify:{id}`, `v1:eval:{case}` |
| **FastAPI + local dashboard** | Read-only view of cached projects | Never fetches or calls LLMs |
| **EEE export (`*.eee.json`)** | Portable eval case for any registry consumer | Schema `eee-2026.07-xingai.1` |
| **eval-registry** | Validate, store, list, show, **diff** records | Private `data/` + CI exit codes |

**Out of scope for this Phase 1 doc:** hosted `*.xingai.app` product UI, PDF ingest, counter-evidence retrieval, multi-tenant auth, production MCP gateway for cite fetch.

### Who (Who should read this?)

- **Enterprise / AI Architects** — worker/cache boundary and eval gate placement
- **Engineering Managers** — what is demo-ready vs production-shaped
- **Platform / CI owners** — how `--fail-on-regression` becomes a gate
- **Product / Research leads** — what “citation coverage” actually means
- **Security reviewers** — SSRF guards, private eval data, no secrets in EEE

### Why (Why does this matter?)

Without this split:

- Dashboards become the **source of truth** → no durable, git-diffable eval history
- Teams invent **one-off JSON scoreboards** → cannot compare Research AI vs Claims vs SAT later
- Absolute claim counts enter CI → longer docs “fail” even when quality is fine
- LLM verify runs leave **no regression gate** → quality drifts unnoticed

With this design:

- One **EEE** shape shared with the EvalEval ecosystem
- Worker compute stays private; registry data stays **private files**
- Ratio metrics (`citation_coverage`, `unsupported_claim_rate`, `unverifiable_rate`) drive the gate
- Local dashboard stays a **viewer**, not a database

### When (When do you need this?)

| Stage | What you need |
|---|---|
| **MVP / demo** | Worker `--no-llm --no-network` + fixture markdown + report.md |
| **Phase 1 — validation (today)** | Full worker + cache + local dashboard + EEE → registry `diff` |
| **Phase 2 — product surfaces** | Research AI / Claims UIs; public demo static export; more consumers |
| **Production** | Private eval store location, retention, auth on APIs, cost accounting |

**Rule:** Ship the **gate** (EEE + diff) before you polish the **product UI**. A pretty dashboard without a regression store is a demo, not a platform.

### Where (Where in the architecture?)

```text
┌─────────────────────────────────────┐
│  Author / Operator                  │
│  Markdown · URL · fixtures          │
└──────────────────┬──────────────────┘
                   ▼
┌─────────────────────────────────────┐
│  evidence-worker (compute)          │  ← Internal System A
│  ingest → extract → verify → metrics│
└──────────┬───────────────┬──────────┘
           │               │
           ▼               ▼
   out/*.md|json|eee    cache.sqlite
           │               │
           │               ▼
           │        FastAPI (read-only) → local dashboard
           ▼
┌─────────────────────────────────────┐
│  eval-registry (governance store)   │  ← Internal System B
│  add · list · show · diff / CI      │
└─────────────────────────────────────┘
```

---

## How It Works

### End-to-end flow

```text
verify CLI → artifacts + cache → (optional) dashboard
                ↓
           *.eee.json → registry add → later: diff --fail-on-regression
```

### Component responsibilities

| Component | Input | Output | Tools / deps |
|---|---|---|---|
| Ingest | Path or URL | Markdown text + sources | httpx; SSRF block on private hosts |
| Extract | Markdown | Claims (+ optional LLM) | Anthropic / OpenAI optional |
| Verify | Sources + claims | Verdicts + evidence quotes | Fetch + `complete_json` |
| Report / metrics | Project | Coverage + rates | Factual-only denominators |
| EEE export | EvaluationCase | Gate ratios + counts in config | Pydantic models |
| Registry | EEE JSON | File under `data/` | Atomic write |
| Diff | Two records | Deltas + `regressions[]` | Old-run `higher_is_better` |

### Example: Radar fixture run

Concrete timeline for `fixtures/2026-07-26-radar.md` (shape of a real Phase 1 run):

```text
Step 1 · Ingest   · parse link defs     · ~40ms  · N sources
Step 2 · Extract  · claim blocks        · ~100ms · factual vs opinion
Step 3 · Sources  · HTTP reachability   · seconds · reachable / blocked / dead
Step 4 · Verify   · LLM support checks  · tens of s · worst multi-cite wins
Step 5 · Export   · report + EEE + cache· ~20ms  · ratios only in metrics
Step 6 · Registry · add + diff vs prior · <10ms  · FAIL if coverage drops
```

**Gate metrics (locked):**

| Metric | Formula | Better when |
|---|---|---|
| `citation_coverage` | cited factual / factual | Higher |
| `unsupported_claim_rate` | (not_supported + uncited) / factual | Lower |
| `unverifiable_rate` | unverifiable / factual | Lower |

Absolute counts (`supported`, `partial`, …) stay under `configuration.counts` so document length does not false-fail CI. Top-level `latency_seconds` is compared by the registry (lower is better).

**Verdict rule that matters:** when multiple cites disagree, **worst support verdict wins** — a refuting page is not masked by a supporting one.

---

## Enterprise Pattern Mapping

| Pattern | How this design applies |
|---|---|
| **Worker / cache boundary** | Worker writes cache; FastAPI only `cache_get` — same Principle 1 as invest-ai |
| **Cache-first before LLM** | Deterministic parse + reachability run without keys; LLM is optional layer |
| **Trace / governance** | Project JSON + EEE `source`/`configuration`/`results` blocks are the durable audit shape |
| **Orchestrator vs MCP Gateway** | Worker is **not** an MCP; cite fetch is direct HTTP with SSRF guard. Domain MCP (if any) is Phase 2+ |
| **Phased roadmap** | Phase 1 validates verification + eval gate; Phase 2 attaches product UIs and more consumers |
| **Observability** | Metrics are first-class ratios with semantics (`higher_is_better`), not hidden chain-of-thought |

---

## Anti-Patterns

| Anti-pattern | Why it fails | Do instead |
|---|---|---|
| Dashboard as source of truth | No durable history; hard to CI | EEE files in eval-registry |
| Absolute counts in the CI gate | Doc length masquerades as quality drop | Export **ratios** only for metrics |
| Best-cite-wins merge | One good cite hides contradiction | Worst support verdict wins |
| `datetime.UTC` / weak path ids | Breaks 3.10; `--project ../x` escapes out | `timezone.utc`; always slugify + contain under `--out` |
| Second invent-a-schema eval JSON | No ecosystem reuse | Stay on EEE four blocks |
| API that re-runs verification | Violates Principle 1; doubles cost/risk | Worker only; API read-only |
| Treating blocked URLs as empty success | Silent zero-claim “success” | Raise on blocked/empty ingest |

---

## POC / Platform Mapping

| Enterprise concept | Phase 1 (today) | Phase 2+ |
|---|---|---|
| Citation verification engine | `xingai-evidence-engine` worker + local UI | Research AI Evidence Workspace; Claims B2B surface |
| Eval store / CI gate | `xingai-eval-registry` CLI + private `data/` | Shared private store; more harnesses (SAT AI, …) |
| Schema | EEE `eee-2026.07-xingai.1` | Upstream EvalEval alignment as ecosystem stabilizes |
| Public demo | Catalog cards on xingai.app; optional static `evidence-demo/` | Hosted product auth and tenancy |
| Cost / token accounting | `cost_usd` nullable | Fill from provider usage |

Repos:

- [xingai-evidence-engine](https://github.com/xingaiapp/xingai-evidence-engine) — [User guide](https://github.com/xingaiapp/xingai-evidence-engine/blob/main/docs/guides/user-guide.md)
- [xingai-eval-registry](https://github.com/xingaiapp/xingai-eval-registry) — [User guide](https://github.com/xingaiapp/xingai-eval-registry/blob/main/docs/guides/user-guide.md)

---

## Related Documents

- [ADR-001 — One engine, two products (Evidence)](https://github.com/xingaiapp/xingai-evidence-engine/blob/main/docs/adr/001-one-engine-two-products.md)
- [ADR-001 — EEE record shape (Registry)](https://github.com/xingaiapp/xingai-eval-registry/blob/main/docs/adr/001-eee-record-shape.md)
- [Orchestrator vs MCP Gateway](2026-06-13-orchestrator-vs-mcp-gateway.md) — orchestration ≠ tool gateway
- [Agent Governance Reference Architecture](2026-07-05-agent-governance-reference-architecture.md) — provenance / audit mindset
- Every Eval Ever — [IBM Research](https://research.ibm.com/blog/every-evaluation-ever) / [EvalEval](https://evalevalai.com/projects/every-eval-ever/)

---

**Author:** Xing Wang  
**Published:** 2026-07-26  
**Tags:** architecture, enterprise, evidence, evaluation, eee, worker-cache, governance
