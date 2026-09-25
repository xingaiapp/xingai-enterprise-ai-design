---
title: Agent Firewall — Phased Roadmap System Design
author: Xing Wang
date: 2026-09-25
tags: [architecture, agent-firewall, policy, risk, hitl, ledger, enterprise]
description: Phased design for XingAI Agent Firewall — harness hooks first, deterministic risk, human approval, decision ledger, MCP gateway later.
---

# Agent Firewall — Phased Roadmap System Design

> *Can a helpful coding agent become the attack surface?*

**Short answer:** Yes. The fix is architectural: every gated tool call passes **policy → risk → approval → ledger**. Models do not get a free pass to the shell.

![Agent Firewall — Phased Roadmap](../assets/agent-firewall-phased-roadmap-system-design-ux.png)

---

## 5W Framework

### What

| Component | Role |
|---|---|
| Harness adapter | Intercept tool calls (Claude Code PreToolUse at v1) |
| Policy engine | YAML → allow \| deny \| review |
| Risk scorer | Deterministic 0–100 (LLM advisory only) |
| Approval queue | Human pause for high risk |
| Decision ledger | Auditable verdicts |
| Dashboard | Queue + audit + trends |

### Who

- Engineers running AI coding agents locally
- Security reviewers of agent tool authority
- Platform teams planning MCP gateway mediation

### Why

Without a firewall: untrusted README / `curl | sh` can execute before a human sees it.  
With it: fail-closed when the engine is down; provenance taint (ADR-004) raises risk after untrusted reads.

### When

| Stage | Need |
|---|---|
| MVP | Local FastAPI engine + hooks + SQLite ledger + Next queue |
| POC | 0din-class demo scenario; latency budget; policy hit stats |
| Production-shaped | Team dashboard deploy; Slack visibility mirror (ADR-006) |
| Phase 2+ | MCP gateway proxy as enterprise interception path |

**Rule:** Harness hooks first; MCP gateway later (ADR-001). Fail closed by default.

### Where

```text
Agent tool call → Adapter hook → Policy → Risk → Approval?
                              ↓
                         Decision ledger → Dashboard
```

---

## How It Works

### Example: DENY / review on `curl | sh`

```text
Step 1 · SessionStart/PostToolUse · untrusted README read → taint
Step 2 · PreToolUse · Bash curl|sh intercepted
Step 3 · Policy + risk → score high (untrusted origin + network + pipe)
Step 4 · Verdict review/deny · approval queue or block
Step 5 · Ledger row written · harness non-zero exit · Completed
```

---

## Enterprise Pattern Mapping

| Pattern | Application |
|---|---|
| Human decides | High-risk execution waits |
| Trace / ledger | Same Decision schema thesis as sibling XingAI products |
| Phased roadmap | Hooks MVP → team ops → MCP gateway |

---

## Anti-Patterns

| Anti-pattern | Why it fails | Do instead |
|---|---|---|
| Trust the model to be careful | Helpfulness is the exploit | Intercept + policy |
| LLM-only risk scoring | Non-deterministic gate | Rules first (ADR-002) |
| Fail open if engine down | Silent bypass | Fail closed |
| Skip ledger | No post-incident truth | Always write Decision |

---

## POC vs Phase 2+

| v1 target | Phase 2+ |
|---|---|
| Claude Code hooks | MCP gateway proxy |
| Local SQLite | Shared team store / hosted dashboard |
| Manual policy YAML | Deny+add-rule workflow (ADR-005) at scale |

---

## Related Documents

- Repo: [xingai-agent-firewall](https://github.com/xingaiapp/xingai-agent-firewall)
- ADRs 001–006 under `docs/adr/`
- Product mirror: `docs/architecture/agent-firewall-phased-roadmap.md`
- 中文: [2026-09-25-agent-firewall-phased-roadmap.zh.md](./2026-09-25-agent-firewall-phased-roadmap.zh.md)
