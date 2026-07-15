---
title: Third-Party MCP Access - API Key or OAuth 2.1? A Decision Framework
author: Xing Wang
date: 2026-07-15
tags: [architecture, enterprise, mcp, oauth, api-design, security, third-party-integration, design-patterns]
description: Teams reflexively reach for a static API key when a first external partner needs to call an MCP server, because it is the fastest thing to ship. This article gives a concrete framework for when that is fine and when it is not, worked through a real progression across three POCs in xingai-enterprise-ai-pocs.
---

# Third-Party MCP Access: API Key or OAuth 2.1? A Decision Framework

The question comes up the moment an MCP server has its first caller outside your own process: does the caller need a static API key, or real OAuth 2.1 with scoped, per-partner tokens? A static key ships in an afternoon. OAuth 2.1 + PKCE + JWT takes real work — an Authorization Server, a JWKS endpoint, token issuance and rotation, scope design. The reflexive answer is almost always "start with the key, we'll add real auth later." Sometimes that's the right call. Often it isn't, and the cost of being wrong doesn't show up until a partner integration is already live.

This isn't a claims-insurance-specific question, but it's easiest to make concrete with one: three POCs in `xingai-enterprise-ai-pocs` worked through exactly this decision at three different points, and the progression across them — `claims-mcp-oauth-poc` (real OAuth from day one), `claims-partner-api-mcp-poc` (static key, explicitly flagged as a gap), `claims-workflow-v2-poc` (static key today, scope names pre-aligned for OAuth tomorrow) — is a useful worked example threaded through this article.

---

## 5W Framework

### What

| | Static API Key | OAuth 2.1 + PKCE + JWT (scoped) |
|---|---|---|
| Granularity | All-or-nothing — one key can call every tool the server exposes | Per-scope (`claims.read`, `payments.write`, ...) — a token can be issued for exactly what a partner needs |
| Revocation | Rotate the shared secret — every legitimate holder is cut off simultaneously | Revoke or let expire one partner's token without affecting others |
| Per-caller identity | None, unless you build your own key-to-partner mapping | Built in — the JWT's `sub` claim ties every call to a specific partner |
| Auditability | "Someone with the key did this" | "Partner X, token issued at T, scope Y, did this" |
| Implementation cost | Minutes | An Authorization Server, JWKS, token issuance/rotation, scope design — days to weeks |
| Best for | Internal-only callers, i.e. nothing has crossed a real trust boundary yet | Any caller outside your own process, especially where money moves or decisions have legal consequences |

### Who

- **Enterprise/AI architects** deciding the auth model for a new externally-facing MCP server
- **Security reviewers** evaluating a third-party integration before it goes live
- **Platform engineers** who inherited a "just use a static key for now" decision and need to know when that stops being acceptable
- **Compliance and legal stakeholders** who need an audit trail tied to a specific external caller, not just "someone with valid credentials"

### When

Before the first external partner is onboarded, not after — retrofitting scoped OAuth onto N already-issued static keys is a partner-coordination problem as much as an engineering one; every partner needs a migration window, and until they've all moved, the server has to support both auth schemes at once. `claims-partner-api-mcp-poc`'s own ADR ([ADR-007](https://github.com/xingaiapp/xingai-enterprise-ai-pocs/blob/main/docs/adr/007-claims-partner-api-mcp-poc-full-coverage.md)) shipped with a static key as a deliberate, explicitly-flagged phase-one gap precisely because the team already knew this migration cost was coming and chose to sequence coverage before auth rather than pretend the gap didn't exist.

### Where

Applies anywhere an MCP (or any API) server has a caller outside the organization's own trust boundary — not limited to claims or insurance. The same tradeoff recurs for payments APIs, healthcare data APIs, HR systems, or any domain with a regulatory audit requirement attached to "who did what."

### Why

Because the two approaches fail differently, and neither failure is loud:

- **A static key fails by silent over-privilege.** A key scoped to "everything this server can do" doesn't announce that it's over-privileged — it just sits there capable of more than any single partner integration actually needs, until a leak or a compromised partner system turns that unused capability into an incident. The failure is invisible until it isn't.
- **OAuth without a second authorization layer fails by mistaking scope for a business limit.** A `claims.adjudicate` scope answers "is this token allowed to adjudicate claims at all" — it says nothing about whether a single adjudication for $500,000 should go through on that token. Scope alone reads as "fully authorized" right up until someone asks the question a business-rule check would have caught.

---

## A Decision Framework

Use a static key when **all** of the following hold:

- The caller is inside your own process or your own infrastructure — no external trust boundary has actually been crossed yet
- There is exactly one caller, so there's no meaningful concept of "which partner did this" to capture
- Nothing the server exposes moves money or produces a legally consequential decision (a denial, an adverse action, a regulatory filing)
- You have an explicit, tracked plan for what replaces the key before a second caller (especially an external one) is onboarded — not "we'll figure it out later"

Move to OAuth 2.1 + PKCE + JWT with per-tool scopes when **any** of the following hold:

- A caller outside your own infrastructure needs access
- Multiple callers need different levels of access to the same server
- You need to answer "which specific caller did this" after the fact, for an audit, an incident investigation, or a regulatory inquiry
- The tools being called move money, deny something, or otherwise produce a decision with real-world consequences for someone who isn't the caller

## Worked Example: Three POCs, Three Points in the Same Decision

[`claims-mcp-oauth-poc`](https://github.com/xingaiapp/xingai-enterprise-ai-pocs/tree/main/pocs/claims-mcp-oauth-poc) built real OAuth 2.1 + PKCE + JWT from the start ([ADR-006](https://github.com/xingaiapp/xingai-enterprise-ai-pocs/blob/main/docs/adr/006-claims-mcp-oauth-poc-real-auth.md)) — its entire purpose was proving the auth protocol itself works for claims adjudication, so a static key would have defeated the point of the POC.

[`claims-partner-api-mcp-poc`](https://github.com/xingaiapp/xingai-enterprise-ai-pocs/tree/main/pocs/claims-partner-api-mcp-poc) shipped with a single static bearer token instead ([ADR-007](https://github.com/xingaiapp/xingai-enterprise-ai-pocs/blob/main/docs/adr/007-claims-partner-api-mcp-poc-full-coverage.md)) — not because auth doesn't matter there, but because that POC's purpose was proving full 18-endpoint API coverage maps cleanly to MCP tools, and building real auth for 18 tools at once would have made it hard to tell whether a bug was in the API mapping or the auth check. The static key is explicitly listed as the #1 "Not Production Yet" item, not a quiet omission — and ADR-007 documents the exact combination plan: put `claims-mcp-oauth-poc`'s Authorization Server in front of this server, enforcing the 10 scopes the OpenAPI contract already declares.

[`claims-workflow-v2-poc`](https://github.com/xingaiapp/xingai-enterprise-ai-pocs/tree/main/pocs/claims-workflow-v2-poc) is the newest point on this line ([ADR-009](https://github.com/xingaiapp/xingai-enterprise-ai-pocs/blob/main/docs/adr/009-claims-workflow-v2-mcp-multiagent.md)). Its MCP server currently has exactly one caller — its own Supervisor process — so a static internal service token is genuinely sufficient today, by the framework above. But its four tools are scoped `policy.read`, `audit.write`, `audit.read`, `payments.write` — reusing `claims-mcp-oauth-poc`'s and `claims-partner-api-mcp-poc`'s existing scope vocabulary instead of inventing new names. The bet: if or when a third-party vendor needs to call this server directly, wiring a real Authorization Server in front of it is a scope-mapping exercise against names that already exist, not a redesign. This is the cheap part of the migration — done at zero cost today, specifically to make the expensive part (issuing and rotating real per-partner credentials) the only thing left when it's actually needed.

## The Two-Wall Model: Why OAuth Scope Alone Isn't Enough Either

`claims-mcp-oauth-poc` doesn't stop at OAuth scope. A token with `claims.adjudicate` still passes through a second, independent check — a settlement-authority policy: a claim-type allowlist and a dollar cap, enforced in code the OAuth layer knows nothing about. This matters because scope answers a yes/no question ("can this token adjudicate claims") that has no dollar amount in it. Wall two is what stops a correctly-scoped but compromised or over-trusted token from authorizing a single catastrophic settlement. Skipping this wall and treating OAuth scope as sufficient is a common enterprise MCP mistake: a broad scope grant reads as "fully authorized," and nothing about OAuth itself will tell you that's not the same claim as "any amount, any claim type, no limit."

## What This Doesn't Solve

Neither a static key nor OAuth 2.1 by itself gets you: rate limiting per partner, tenant data isolation, key/token compromise detection, or a real incident-response runbook for a leaked credential. Those are separate design questions this article doesn't cover — the point here is narrower: pick the right authentication primitive for the trust boundary you actually have, and be honest in your own design docs about which one you've built versus which one you're planning to.

## Related

- [ADR-006: Claims MCP OAuth POC — real auth, not a placeholder](https://github.com/xingaiapp/xingai-enterprise-ai-pocs/blob/main/docs/adr/006-claims-mcp-oauth-poc-real-auth.md) — source of the two-wall model
- [ADR-007: Claims Partner API MCP POC — full API coverage, auth deferred](https://github.com/xingaiapp/xingai-enterprise-ai-pocs/blob/main/docs/adr/007-claims-partner-api-mcp-poc-full-coverage.md) — source of the "align scope names now, wire auth later" pattern
- [ADR-009: Claims Workflow v2 — MCP tool access, LLM agents, LangGraph supervisor](https://github.com/xingaiapp/xingai-enterprise-ai-pocs/blob/main/docs/adr/009-claims-workflow-v2-mcp-multiagent.md) — this article's newest worked example
- [MCP API Coverage vs. Workflow Tools](2026-07-13-mcp-api-coverage-vs-workflow-tools.md) — a related tradeoff (tool surface, not auth) using the same two POCs
- [How MCP Works in Production: A Deep Dive from Robinhood Trading MCP](2026-07-11-mcp-in-production-robinhood-case.md) — the two-wall model's origin, ported here from a brokerage domain
- [Agent Governance Reference Architecture](2026-07-05-agent-governance-reference-architecture.md) — the broader authority/provenance/approval/audit framework this article's auditability point sits inside
