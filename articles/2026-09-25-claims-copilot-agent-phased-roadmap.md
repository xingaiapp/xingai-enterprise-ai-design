---
title: Claims Copilot Agent — Phased Roadmap System Design
author: Xing Wang
date: 2026-09-25
tags: [architecture, claims, agent, mcp, hitl, evaluation, enterprise]
description: Phased system design for Claims Copilot — MVP tool loop through production-shaped Entra ID, OBO, HITL, MCP, and golden evaluation.
---

# Claims Copilot Agent — Phased Roadmap System Design

> *What separates a claims chatbot from an enterprise Claims Copilot Agent?*

**Short answer:** Tools with schemas, delegated identity, human approval on writes, citations, and a golden evaluation set — not a prettier prompt.

![Claims Copilot Agent — Phased Roadmap System Design](../assets/claims-copilot-agent-phased-roadmap-system-design-ux.png)

---

## 5W Framework

### What

| Layer / Component | Role | Owns |
|---|---|---|
| Claims Copilot UI | Adjuster surface | Request, preview, approve |
| Agent API (.NET) | Authn boundary | JWT validation, request_id |
| Orchestrator | Agent loop | Plan → tool → observe → stop |
| LLM | Reason / draft | Never authoritative authz |
| MCP tool layer | Enterprise adapters | Claim, Policy, Notes APIs |
| Eval + Observability | Proof | Golden Dataset, OTel traces |

**Out of scope here:** confidential carrier SOPs, production claim schemas, live Twilio/XNP wiring.

### Who

- **Solution architects** joining claims programs — pattern and phase boundaries
- **Engineers** building the lab — tool allowlists, HITL, OBO
- **Security / compliance** — who can write Notes, how audit works
- **Hiring managers** — what “enterprise Agent” evidence looks like

### Why

Without this design:

- Models invent claim facts; writes skip approval
- Token passthrough blurs who acted
- Prompt edits silently regress quality

With it:

- Reads automate; sensitive writes wait for a human
- Downstream APIs see OBO tokens and re-authorize
- Regressions show up in golden runs before demos

### When

| Stage | What you need |
|---|---|
| MVP / demo | Single Agent, mock Claim/Policy tools, structured summary |
| POC validation | MCP server stubs, citation fields, HITL on `add_claim_note` |
| Production-shaped | Entra ID + OBO, RBAC on tools, audit ledger, PII redaction in logs |
| Phase 2+ | Multi-Agent Review only after single-Agent eval is green; optional Service Bus |

**Rule:** One Agent with hard tool bounds before Multi-Agent fan-out.

### Where

```text
Adjuster → Copilot UI → Agent API → Orchestrator → LLM
                                      ↓
                                   MCP Client
                                      ↓
                         Claim | Policy | Notes APIs
                                      ↓
                         Audit / Golden Eval / OTel
```

---

## How It Works

### End-to-end flow

```text
Request → authorize → load context → reason → allowlisted tools
→ cite sources → recommend → (if write) HITL → audit → respond
```

### Example: summarize + recommend (HITL on note)

```text
Step 1 · API · JWT ok · 12ms
Step 2 · Orchestrator · get_claim(CLM-10023) · 120ms
Step 3 · Orchestrator · search_claim_notes · 80ms
Step 4 · Orchestrator · get_policy · 95ms
Step 5 · LLM · draft summary + next action · citations attached
Step 6 · UI · preview add_claim_note · PENDING human
Step 7 · Human · APPROVE · Note written · audit row · Completed
```

---

## Enterprise Pattern Mapping

| Pattern | Application |
|---|---|
| Orchestrator vs MCP Gateway | Orchestrator decides; MCP exposes tools — no “Orchestration MCP” |
| Trace / governance | request_id, tools, durations, accept/reject |
| Phased roadmap | MVP tools → POC MCP/HITL → prod identity → optional multi-agent |
| Cache-first before LLM | Prefer retrieved claim facts over free invent |

---

## Anti-Patterns

| Anti-pattern | Why it fails | Do instead |
|---|---|---|
| Chatbot that “sounds right” | Unverified facts enter decisions | Required facts + citations |
| Auto-write Notes | Compliance and audit gaps | HITL for writes |
| Token passthrough | Wrong audience, blurry authz | OBO + downstream authz |
| Multi-Agent day one | Cost, latency, debug hell | Prove single Agent first |
| Invented resume metrics | Credibility loss | Label Prototype / simulated |

---

## POC vs Phase 2+

| Validated in teaching POC | Phase 2+ / production |
|---|---|
| Tool loop + mock data | Live Claims/Policy systems |
| HITL UX sketch | Real Entra roles + audit store |
| Golden set (≥20 cases) | Continuous regression in CI |
| Manual injection sample | Automated adversarial suite |

---

## Related Documents

- Course: [Claims Copilot Agent Engineering](../courses/claims-copilot-agent/README.md) · [中文](../courses/claims-copilot-agent/README.zh.md)
- Architecture mirror: [docs/architecture/claims-copilot-agent.md](../docs/architecture/claims-copilot-agent.md)
- Claim Business: [courses/claim-business](../courses/claim-business/README.md)
- Identity deep dive: [Course 10 OAuth/OIDC](../courses/10-oauth-oidc-azure-identity/README.md)
- 中文: [2026-09-25-claims-copilot-agent-phased-roadmap.zh.md](./2026-09-25-claims-copilot-agent-phased-roadmap.zh.md)
