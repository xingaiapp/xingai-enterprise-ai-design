---
title: MCP API Coverage vs. Workflow Tools - A Claims Partner Integration Case Study
author: Xing Wang
date: 2026-07-13
tags: [architecture, enterprise, mcp, api-design, tool-gateway, insurance, claims, design-patterns]
description: When you wrap an existing REST API as MCP tools, do you expose every endpoint or a handful of hand-picked workflows? This article works through the tradeoff using two sibling claims-domain POCs — one narrow with real OAuth, one broad with no auth yet — and gives a framework for choosing.
---

# MCP API Coverage vs. Workflow Tools: A Claims Partner Integration Case Study

Every team wrapping an existing REST API as an MCP server hits the same fork almost immediately: expose every endpoint the API has, one tool per operation — or pick a small number of higher-level workflow tools that bundle several API calls into one agent-facing action? Demos rarely show this decision being made; they show the tool list *after* someone already decided.

This article works through the tradeoff concretely, using two sibling proof-of-concept projects in `xingai-enterprise-ai-pocs` that deliberately took opposite sides of it: [`claims-mcp-oauth-poc`](https://github.com/xingaiapp/xingai-enterprise-ai-pocs/tree/main/pocs/claims-mcp-oauth-poc) (4 hand-picked tools, real OAuth 2.1 + PKCE) and [`claims-partner-api-mcp-poc`](https://github.com/xingaiapp/xingai-enterprise-ai-pocs/tree/main/pocs/claims-partner-api-mcp-poc) (18 tools, full CRUD, no auth layer yet). Neither is "the right answer" — they answer different questions, and a real deployment needs both answers combined.

---

## 5W Framework

### What

Two designs for turning a REST API into MCP tools:

| | Full API coverage | Narrow workflow tools |
|---|---|---|
| Tool count | One tool per endpoint (or close to it) | A handful, each bundling multiple API calls |
| Agent flexibility | High — agent composes operations itself | Low — agent can only do what the workflow allows |
| Review surface | Large — every endpoint is a tool an auditor must reason about | Small — a fixed, auditable set of actions |
| Time to "done" | Fast — mechanical mapping from OpenAPI spec to tool schema | Slower — someone has to design each workflow's shape |
| Where business rules live | Scattered across whichever tool a caller happens to invoke, or pushed into the backend | Concentrated in the workflow tool itself (e.g. a Review→Adjudicate split) |

### Who

- **Enterprise/AI architects** deciding how to expose an internal or partner-facing API through MCP
- **Platform engineers** building the first MCP server for a domain and choosing a starting scope
- **Security reviewers** who need to reason about what a granted token can actually do
- **Product managers** scoping a third-party integration's first release

### When

This decision has to be made **before** writing the first tool, not discovered afterward — the two POCs referenced here started from the same OpenAPI-shaped domain (insurance claims) and diverged at exactly this fork, which is why comparing them side by side is useful: same domain, same underlying operations, opposite choices.

### Where

Applies anywhere an MCP server sits in front of an existing or newly-designed REST/GraphQL API: claims systems, CRMs, ticketing systems, payment processors, HR systems — any domain where "just wrap the API" is the obvious first instinct and the real question is how literally to take "wrap."

### Why

Because the choice has consequences that are expensive to reverse later. Ship full coverage first and you may have to retrofit fine-grained authorization onto 18 tools instead of 4. Ship narrow workflow tools first and partners hit a wall the moment their use case needs an operation you didn't anticipate — and now you're either adding tools reactively (drifting back toward full coverage anyway) or turning away integration requests.

---

## The Two POCs, Side by Side

[`claims-mcp-oauth-poc`](https://github.com/xingaiapp/xingai-enterprise-ai-pocs/tree/main/pocs/claims-mcp-oauth-poc) exists to prove something specific: that a real OAuth 2.1 + PKCE + JWT authentication protocol, plus a two-wall authorization model (OAuth scope *and* an independent settlement-authority policy check), generalizes cleanly from a brokerage domain to insurance claims. To keep that proof legible, its tool surface is deliberately narrow — `get_claim`, `get_policy_coverage`, `review_claim_decision`, `submit_claim_decision` — four tools, each one easy to reason about against the auth machinery sitting in front of it. Nobody reviewing that POC has to wonder what fifteen other tools might also be reachable with a `claims.adjudicate` scope.

[`claims-partner-api-mcp-poc`](https://github.com/xingaiapp/xingai-enterprise-ai-pocs/tree/main/pocs/claims-partner-api-mcp-poc) exists to prove the opposite thing: that a claims business's *entire* partner-facing API surface — claim intake, status transitions, notes, document evidence, policy coverage checks, claimant management, settlement payments, 18 endpoints across 7 domains defined in a single OpenAPI 3.1 contract — can be mapped one-to-one into MCP tools without the mapping becoming inconsistent or unreviewable, and that the resulting server is genuinely runnable end to end (a small Express mock upstream implements the same contract, so the whole stack runs via `docker compose up`). To keep *that* proof clean, it deliberately ships with **no** third-party authentication layer yet — adding real OAuth to 18 tools at once would have made it harder to tell whether a bug was in the API mapping or in the auth check.

Put differently: `claims-mcp-oauth-poc` answers "does the auth protocol work and generalize"; `claims-partner-api-mcp-poc` answers "can the whole API surface be covered without the mapping falling apart." Neither POC tried to answer both questions at once on purpose — see [ADR-007](https://github.com/xingaiapp/xingai-enterprise-ai-pocs/blob/main/docs/adr/007-claims-partner-api-mcp-poc-full-coverage.md) for the explicit reasoning.

## What a Real Deployment Needs From Both

A production third-party claims integration is not "pick one of these two POCs and ship it" — it's `claims-partner-api-mcp-poc`'s breadth of coverage with `claims-mcp-oauth-poc`'s Authorization Server put in front of it, enforcing per-tool OAuth scopes (`claims.read`, `claims.write`, `claims.adjudicate`, `documents.read`, `documents.write`, `policies.read`, `claimants.read`, `claimants.write`, `payments.read`, `payments.write` — already declared in `claims-partner-api-mcp-poc`'s OpenAPI contract, just not enforced yet). Neither POC alone is safe to hand to a real third party: the narrow one doesn't cover enough of the API to be useful for anything beyond the one workflow it was built for, and the broad one has no way to tell one partner's credential from another's.

This is the practical resolution of the tradeoff, not a compromise that waters down either side: **build the coverage and the auth as separately reviewable pieces, then combine them.** Trying to build both at once, in one POC, tends to produce a result where reviewers can't cleanly evaluate either property — is this tool missing because the API mapping is incomplete, or because the auth scope excludes it on purpose? Keeping them apart until each is independently correct removes that ambiguity.

## A Rough Decision Guide

- **Start narrow (workflow tools) when:** the calling agent's use case is well understood and fixed (one workflow, like claim adjudication assist), the operation is high-stakes enough that every tool needs individual security review, or you're validating a *protocol* (like auth) and don't want tool count to be a confounding variable.
- **Start broad (full coverage) when:** you don't yet know how third-party agents will actually use the API and don't want to guess wrong, the API is already well-specified (an OpenAPI contract exists or is easy to write), and the immediate goal is proving the wrap-an-existing-API-as-MCP mechanics work end to end.
- **Plan to combine them** the moment "start broad" work is real enough that real third parties might touch it — full coverage without per-tool authorization is a liability, not a feature, past the prototype stage.

## Related

- [ADR-007: Claims Partner API MCP POC — Full API Coverage, Auth Deferred](https://github.com/xingaiapp/xingai-enterprise-ai-pocs/blob/main/docs/adr/007-claims-partner-api-mcp-poc-full-coverage.md)
- [ADR-006: Claims MCP OAuth POC — Real Auth, Not a Placeholder](https://github.com/xingaiapp/xingai-enterprise-ai-pocs/blob/main/docs/adr/006-claims-mcp-oauth-poc-real-auth.md)
- [pocs/claims-partner-api-mcp-poc/](https://github.com/xingaiapp/xingai-enterprise-ai-pocs/tree/main/pocs/claims-partner-api-mcp-poc) — this article's direct implementation
- [pocs/claims-mcp-oauth-poc/](https://github.com/xingaiapp/xingai-enterprise-ai-pocs/tree/main/pocs/claims-mcp-oauth-poc) — the auth layer the above POC is missing
- [How MCP Works in Production: A Deep Dive from Robinhood Trading MCP](2026-07-11-mcp-in-production-robinhood-case.md) — production MCP concerns beyond tool-surface design
- [Build an OAuth 2.1 + PKCE MCP Project from Scratch](../guides/2026-07-12-mcp-oauth-pkce-lab.md) — the auth pattern referenced throughout this article
