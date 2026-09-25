# From Toy Demo to Enterprise AI Agent

A single-lesson course on the gap between an Agent that demos well and an Agent that can be operated. Uses **Claims Copilot** as its spine case, but the engineering content is domain-independent.

## Documents

| Language | File |
|----------|------|
| English | [toy-demo-to-enterprise-agent-guide-en.md](./toy-demo-to-enterprise-agent-guide-en.md) |
| 简体中文 | [toy-demo-to-enterprise-agent-guide-zh.md](./toy-demo-to-enterprise-agent-guide-zh.md) |

Both files are full peers. Chinese keeps technical terms in English on first use.

## Audience

- Engineers who can already call an LLM API but have never shipped an Agent
- Anyone preparing an Agent project for a resume or a systems-design interview
- Architects who need a shared vocabulary for "is this production-ready?"

**Not required:** production Agent experience, a specific Agent framework, or insurance background.

## What this lesson argues

> Enterprise-grade does not mean a heavier stack. It means **designed for failure**.

The lesson separates Demo from production along four axes — Business Logic, System Architecture, Objective, Value Evaluation — and gives a five-stage upgrade path with acceptance criteria and the usual ways each stage goes wrong.

## The load-bearing section

**§5.4 — the denominator must be reproducible.** Most Agent curricula publish a metrics table (`Required Fact Coverage ≥95%`) without asking what the 95% is measured against. If an LLM decides which facts were required, the denominator moves between runs and the metric cannot detect a regression. This is not hypothetical: `xingai-evidence-engine` ADR-004 records a measured 4-vs-2 swing on identical input from an unset temperature.

If you read one section, read that one.

## Contents

| § | Topic |
|---|---|
| 1 | The four differences, and the one question that separates Demo from production |
| 2 | Business Logic — the ten-step closed loop, including the failure and rejection branches |
| 3 | System Architecture — capability checklist, idempotency, On-Behalf-Of, prompt injection |
| 4 | Objective — when **not** to use an Agent (decision tree) |
| 5 | Value Evaluation — baselines, reproducible denominators, eval-set design, real token cost |
| 6 | Five-stage upgrade path with per-stage acceptance criteria |
| 7 | Newbie → Expert capability ladder |
| 8 | Resume-project checklist, and what interviewers follow up on |
| 9 | Seven anti-patterns |
| 10 | Exercises with full answer key, including the authorization/injection test case |

## Related XingAI material

- Domain background: [Claim Business Course](../claim-business/README.md)
- Agent build-out for this same case: [Claims Copilot Agent](../claims-copilot-agent/README.md)
- Identity mechanics: [MCP OAuth deep dive](../../guides/2026-07-12-mcp-oauth-auth-deep-dive.md) · [PKCE lab](../../guides/2026-07-12-mcp-oauth-pkce-lab.md)
- Course contract: [../COURSE-STANDARD.md](../COURSE-STANDARD.md)

## Accuracy posture

Architecture diagrams, API shapes, tool names, and metric targets are **illustrative design** — they do not describe any production system. Claims examples inherit the accuracy boundaries of the [Claim Business Course](../claim-business/README.md): real workflows depend on Client Instructions, Service Agreements, policy terms, jurisdiction, and delegated authority. Not legal, compliance, or investment advice.
