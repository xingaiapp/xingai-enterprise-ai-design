---
title: Golden Pit Opportunity Radar — Phased Roadmap System Design
author: Xing Wang
date: 2026-09-25
tags: [architecture, invest-ai, golden-pit, worker-cache, adr-041, enterprise]
description: Phased design for Golden Pit inside Invest AI — deterministic worker score, read-only API, honest Grade A gates, cache consumers.
---

# Golden Pit Opportunity Radar — Phased Roadmap System Design

> *When a stock is down 30%, is that a Golden Pit?*

**Short answer:** Only if hard gates pass — intact thesis, valuation evidence, fresh data, acceptable portfolio impact. Deep drawdown alone never earns Grade A. LLM must not invent the score.

![Golden Pit Opportunity Radar — Phased Roadmap](../assets/golden-pit-opportunity-radar-phased-roadmap-system-design-ux.png)

---

## 5W Framework

### What

| Component | Role |
|---|---|
| `market_cache_worker/golden_pit/` | Deterministic `GoldenPitScore` + grades |
| SQLite KV cache | `v1:golden-pit:latest`, history, alert-dedup |
| FastAPI `/api/v2/golden-pit*` | Read-only cache surface (ADR-012) |
| FE `/golden-pit` | Radar + detail + local watchlist filter |
| Daily Intelligence / 智报 | Same cache — no second scorer |

**Out of scope:** New `golden-pit.xingai.app` product (rejected, ADR-032 pattern).

### Who

- Invest AI engineers extending worker/API/FE
- Product owners who want “buy the dip” honesty
- Readers of ADR-041 and report consumers

### Why

Without honesty gates: fabricated Grade A, invented position sizes, LLM override.

With this design: empty Grade A is a feature (“no trade better than forcing”); Attention Score stays separate from pit quality.

### When

| Stage | Need |
|---|---|
| MVP | Worker engine + cache + read API + FE + no-A messaging |
| POC | Report sections + alert dedup skeleton + unit tests |
| Production-shaped | Live bars/quotes on refresh; fail soft if pit refresh fails |
| Phase 2+ | Honest fundamentals/valuation feeds, real holdings, richer alerts |

**Rule:** Missing / UNKNOWN / stale / BROKEN / leveraged / WeeklyPay → block Grade A.

### Where

```text
Worker refresh → golden_pit engine → cache
FE / Reports / Alerts → FastAPI read-only → cache
LLM explanations = templates from fields only
```

---

## How It Works

```text
Scan watchlist → score components → hard gates → grade
→ write latest + history → optional Grade-A alert dedup
→ UI shows principle when grade_a_count = 0
```

### Example: no Grade A day

```text
Step 1 · Worker · refresh dashboard + golden_pit
Step 2 · Engine · NVDA thesis UNKNOWN → fail thesis_intact
Step 3 · Cache · grade_a_count=0 · messages ZH/EN written
Step 4 · FE · “今日无 A 级黄金坑” · Completed
```

---

## Enterprise Pattern Mapping

| Pattern | Application |
|---|---|
| Worker / cache boundary | Worker scores; API never recalculates |
| Trace / honesty | Failed gates and missing evidence are explicit |
| Phased roadmap | MVP radar → reports/alerts → live fundamentals |

---

## Anti-Patterns

| Anti-pattern | Why it fails | Do instead |
|---|---|---|
| Score on FastAPI request path | Breaks ADR-012 | Worker-owned cache |
| LLM overrides grade | Undermines honesty | Template explanations |
| Promote drawdown to A | Forces bad trades | Critical hard gates |
| Invent portfolio weights | Lying to the user | “Portfolio impact unavailable” |

---

## POC vs Phase 2+

| Shipped (MVP/POC) | Phase 2+ |
|---|---|
| Deterministic engine + tests | Authoritative fundamental feeds |
| Default watchlist scan | Holdings-driven portfolio limits |
| Alert dedup skeleton | Full notification product path |

---

## Related Documents

- ADR-041: [xingai-invest-ai](https://github.com/xingaiapp/xingai-invest-ai/blob/main/docs/adr/041-golden-pit-opportunity-radar.md)
- Product mirror: [invest-ai docs/architecture](https://github.com/xingaiapp/xingai-invest-ai/blob/main/docs/architecture/golden-pit-opportunity-radar.md)
- 中文: [2026-09-25-golden-pit-opportunity-radar-phased-roadmap.zh.md](./2026-09-25-golden-pit-opportunity-radar-phased-roadmap.zh.md)
