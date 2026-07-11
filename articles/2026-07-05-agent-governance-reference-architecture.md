---
title: Agent Governance Reference Architecture - Authority, Provenance, Approval, Audit
author: Xing Wang
date: 2026-07-05
tags: [architecture, enterprise, agent-security, governance, human-in-the-loop, prompt-injection, audit, policy-engine]
description: Enterprises are deploying agents that can execute commands, move tickets, and spend money — with no equivalent of a firewall for agent actions. This article gives a reference architecture with five governance planes, grounded in a working implementation, not slideware.
---

# Agent Governance Reference Architecture: Authority, Provenance, Approval, Audit

Every enterprise agent conversation eventually reaches the same question, usually asked by the most senior person in the room:

> *What exactly can this agent do without asking anyone — and where is the record when it does?*

Most teams answer with model-level assurances ("the system prompt forbids it"). That answer fails review, and it should: Mozilla's 0din team demonstrated that a clean-looking GitHub repository can steer a coding agent into executing malicious commands. The injection arrives through content the agent is *supposed* to read. A rule written in the prompt cannot bind an agent whose input stream is attacker-reachable.

Microsoft's developer research ("To Copilot and Beyond") points at the shape of the real answer: what people actually want from agents is **bounded delegation** — real autonomy inside an explicit, inspectable boundary. Governance is the system that makes the boundary real.

This article gives that system a reference architecture: five planes, each with a concrete implementation you can inspect. None of this is slideware — the primary reference implementation (`xingai-agent-firewall`) runs today, and the pattern has shipped three times in domain-specific form (trade gates, prediction-market gates, claims adjudication escalation).

---

## The core inversion

Traditional security asks *who is the user and what may they access* (authN/authZ). Agent governance asks a different question:

> **The principal is already authorized. What may the agent do on their behalf, under instructions nobody fully controls?**

That inversion is why IAM, DLP, and network policy don't cover this: the agent operates *inside* the user's session, with the user's permissions, but its behavior is a function of every document, repo, and webpage it reads. The threat model is not the malicious outsider; it is the **tricked insider that operates at machine speed**.

## Five governance planes

```
        Agent intent (tool call / order / write / message)
                          │
  ┌───────────────────────▼───────────────────────────┐
  │ 1. AUTHORITY PLANE     what needs no approval,     │
  │    (declared scope)    what needs it, what never   │
  ├────────────────────────────────────────────────────┤
  │ 2. POLICY PLANE        deterministic rules +       │
  │    (the gate)          weighted signals →          │
  │                        allow | deny | review       │
  ├────────────────────────────────────────────────────┤
  │ 3. APPROVAL PLANE      review holds synchronously; │
  │    (human-in-loop)     timeout resolves to deny    │
  ├────────────────────────────────────────────────────┤
  │ 4. PROVENANCE PLANE    where did this instruction  │
  │    (origin tracking)   come from? trusted config   │
  │                        vs. just-fetched content    │
  ├────────────────────────────────────────────────────┤
  │ 5. AUDIT PLANE         one Decision row per        │
  │    (the ledger)        verdict, incl. overrides    │
  └────────────────────────┬───────────────────────────┘
                           ▼
              effect executes (or never does)
```

### 1. Authority plane — bounded delegation, written down

Each agent surface declares three lists: **acts freely** (read, search, draft), **needs approval** (execute, write outside workspace, spend), **never** (exfiltrate credentials, bypass its own gate). This is the document enterprise buyers actually ask for, and it doubles as the test spec: the acceptance suite for our claims-adjudication POC tests exactly one property above all — *no claim above the escalation threshold is ever auto-decided*.

### 2. Policy plane — the judge must not be promptable

The allow/deny decision comes from deterministic rules: named signals with weights, thresholds in config, same input → same verdict, every fired rule listed. In the firewall implementation: `shell_pipe_from_network` +40, `secrets_path_access` +35, seven signals total, YAML-configured.

The tempting alternative — asking an LLM "is this dangerous?" — recreates the vulnerability one layer down: a judge that reads attacker-controlled content is itself injectable. An LLM may contribute an *advisory* signal that raises scrutiny. It must never be able to authorize what rules deny.

### 3. Approval plane — synchronous, fail-closed

`review` verdicts hold the action open while a human decides, with four resolutions: approve once, approve for session, deny, deny-and-add-rule. Deny-and-add-rule is two layers, not one write ([Agent Firewall ADR-005](https://github.com/xingaiapp/xingai-agent-firewall/blob/main/docs/adr/005-deny-add-rule.md)): an instant, reversible **pinned deny** stops the exact call from re-entering the queue; a **rule suggestion** queues the durable YAML change for human review. The runtime never rewrites `policies/*.yaml` itself — config that enforces agent behavior stays reviewed like code.

Two defaults are non-negotiable: **timeout resolves to deny**, and **gate unreachable means blocked**. Fail-closed must hold end-to-end — an approval system that fails open is an audit system wearing a costume.

Asynchronous approval (fail now, retry after approval) sounds cleaner and is worse: the agent treats the failure as an error and improvises around it — exactly the behavior a governance layer must not provoke.

A second implementation, [`xingai-robinhood-mcp` ADR-001](https://github.com/xingaiapp/xingai-robinhood-mcp/blob/main/docs/adr/001-mcp-gateway-proxy.md), moves the interception point itself: not a harness hook, but a local **MCP gateway proxy** the client connects to instead of the third-party MCP endpoint directly — necessary once a tool is used from several harnesses (Cursor, Claude Code, ChatGPT), none of which share a hook contract. It also sharpens the fail-closed discipline one level further: of Invest AI ADR-028's seven trade gates, three (human confirm, account-scope check, audit log) run as real code here; the other four are not stubbed to pass — each rejects by name ("G3 data freshness not wired") until the cross-repo dependency it needs actually exists. A governance layer that cannot yet enforce a gate must say so per-gate, not average it away into a checklist that looks complete.

### 4. Provenance plane — trust is a property of origin

The 0din attack works because instructions from a just-cloned README carry the same weight as the user's typed request. Governance requires the opposite: instructions traceable to untrusted origins (fresh repos, fetched pages, inbound documents) raise the risk score of any action they trigger.

This plane is **shipped** in the firewall reference implementation ([ADR-004](https://github.com/xingaiapp/xingai-agent-firewall/blob/main/docs/adr/004-origin-provenance-tracking.md)), not aspirational. Mechanism: session-start `git ls-files` baseline; PostToolUse taint on Read/Grep/Glob/WebFetch/WebSearch; clear on UserPromptSubmit (turn scope, not a time window). The engine derives `untrusted_origin_instruction` from session taint — the PreToolUse hook stays thin. Same 0din reproduction moves from risk 60 (`review`) to 80 (`deny`) once the agent has read the malicious README this turn.

Honest boundaries remain: non-git projects get web provenance only; cross-turn delayed attacks are a migration trigger, not v1 coverage. Provenance fails *open* on this signal alone — missing baseline never invents false denials; the other policy signals still fire.

### 5. Audit plane — one schema, every verdict

Every gated action writes one decision row: what was attempted, which rules fired, what the verdict was, who overrode it, what actually executed. Two design choices matter:

- **Overrides are first-class data.** A human approving what rules flagged (or denying what rules allowed) is the highest-value signal for tuning weights — surface override-rate per rule. Frequently pinned patterns (ADR-005) are the same signal in another form: a YAML rule is overdue.
- **One shared schema across products.** XingAI's Decision Ledger schema now has six adopters across trading, meals, learning, research, and agent security. The cross-product audit view costs nothing extra because the shape was shared from day one.

## Reference implementations

| Plane | General implementation | Domain-specific precedents |
|---|---|---|
| Authority | firewall threat-model + gated-category config | Invest AI ADR-028 (G1–G7 trade gates), claims POC escalation thresholds |
| Policy | YAML signal engine (deterministic) | fraud checks "rules first, LLM second" |
| Approval | approval queue, timeout→deny, pin + suggestion (ADR-005) | trade confirm modals, Telegram confirm, Robinhood MCP gateway G1 (`xingai-robinhood-mcp` ADR-001) |
| Provenance | turn-scoped session taint + baseline (ADR-004) | citation-grounded RAG (no uncited text reaches the adjudicator) |
| Audit | Decision Ledger schema | audit_trail tables, decision snapshots, Robinhood MCP gateway G7 (`xingai-robinhood-mcp` ADR-001) |

The pattern is codified as `agent-execution-gate` in the XingAI engineering system, with a per-product adoption checklist — a new execution surface adopts by writing a one-page ADR mapping the five planes onto itself.

## What to avoid

- **Prompt-only governance** — a request, not a gate; injection walks past it.
- **A central gate service for everything** — each product gates its own surface with its own signals; share the pattern and the ledger schema, not a runtime dependency.
- **Audit without prevention** — by audit time, the payload ran.
- **LLM-as-judge in the verdict path** — advisory only, capped, never authorizing.
- **Runtime rewriting of policy YAML** — pins are runtime state; durable rules stay git-reviewed.
- **Skipping the honest threat model** — every gate must state what it does *not* stop (the firewall stops a tricked agent, not a malicious local user with settings access). A governance story that claims completeness fails diligence; one that states its boundary passes.

## Adoption path

1. **Week 1:** declare authority scope for one agent surface; wire an interception point the agent cannot route around (harness hook, gateway, or gate function); ship deterministic policy + fail-closed check.
2. **Week 2:** approval flow with timeout-to-deny; turn-scoped provenance if the surface reads untrusted content (repos, web, inbound docs).
3. **Week 3:** ledger rows + override-rate view; pin + suggestion for durable policy (not live YAML mutation); regression corpus in CI (known-bad never silently allowed, known-good never blocked).
4. **Then:** per-team policy inheritance, fleet dashboards, multi-harness adapters — *after* the single-surface loop works end-to-end.

Agents will keep getting stronger. The enterprise question is already shifting from "how capable is your agent" to **"what can it do without asking, who approves the rest, and where's the record."** The teams that can answer with an architecture diagram and a ledger query — not a system prompt — are the ones that will get to deploy.
