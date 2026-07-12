---
title: How MCP Works in Production - A Deep Dive from Robinhood Trading MCP
author: Xing Wang
date: 2026-07-11
tags: [architecture, enterprise, mcp, oauth, agents, tool-gateway, governance, broker-integration, human-in-the-loop]
description: MCP demos look like "connect a URL and call tools." Production is transport mismatch, OAuth redirect fights, tool catalogs with write side effects, and product gates sitting above the protocol. This article walks the real Cursor → mcp-remote → Robinhood Trading MCP path end to end.
---

# How MCP Works in Production: A Deep Dive from Robinhood Trading MCP

Enterprise decks describe MCP as:

> *An open standard so AI agents can call external tools.*

That sentence is true and almost useless. It does not tell you why Cursor's native OAuth callback fails against a broker, why `tools/list` is a security control, or why "the MCP can place trades" is not the same as "your product should place trades."

This article is a **deep, real-case** walkthrough of Model Context Protocol using XingAI's live integration with **Robinhood Trading MCP** (`https://agent.robinhood.com/mcp/trading`) from **Cursor**. The goal is architectural understanding for enterprise architects — not a Robinhood tutorial, and not investment advice.

**Companion docs (implementation):** [xingai-robinhood-mcp](https://github.com/xingaiapp/xingai-robinhood-mcp) · Invest AI [ADR-028](https://github.com/xingaiapp/xingai-invest-ai/blob/main/docs/adr/028-robinhood-mcp-execution-gates.md) · [OAuth troubleshooting](https://github.com/xingaiapp/xingai-robinhood-mcp/blob/main/docs/robinhood-mcp-oauth-troubleshooting.md)

**Education guides (auth + lab):** [MCP Auth deep dive — OAuth 2.1 / PKCE / JWT](../guides/2026-07-12-mcp-oauth-auth-deep-dive.md) · [Build OAuth 2.1 + PKCE MCP from scratch](../guides/2026-07-12-mcp-oauth-pkce-lab.md) · [中文](../guides/README.md)

---

## 5W Framework

### What

MCP is a **client–server protocol** for:

1. **Discovering** capabilities (`tools/list`, optionally resources/prompts)
2. **Invoking** them (`tools/call`) with structured arguments
3. **Returning** structured results the agent can feed back into the next model turn

In production you also get: **transports** (stdio vs Streamable HTTP), **auth** (often OAuth), **host identity** (who is the MCP client — Cursor, Claude, your gateway), and **authorization semantics** that live *inside* tool implementations (e.g. `agentic_allowed`).

### Who

- Enterprise / AI architects designing agent ↔ SaaS tool access
- Platform engineers wiring Cursor / Claude / custom hosts to hosted or internal MCP servers
- Security teams reviewing OAuth redirect, token storage, and write-tool blast radius
- Product owners who must place **gates above** whatever the vendor MCP allows

### Why

Vendor MCP servers are shipping for brokerage, CRM, cloud, and DevOps. Teams that treat MCP as "another REST wrapper" miss the failure modes that only appear at auth and write boundaries. Robinhood's Agentic Trading MCP is a sharp teaching case: **read is broad, write is narrow, confirmation is optional at the broker, and the host's OAuth client may not match the vendor's allowlist.**

### When

| Stage | What MCP gives you | What you still must build |
|-------|--------------------|---------------------------|
| Demo | Tools appear in the host | Nothing — until the first OAuth error |
| Personal agent | Hosted MCP + user OAuth | Local bridge, token hygiene |
| Product integration | Same tools | Product gates, ledger, UX confirm (ADR-028) |
| Enterprise platform | Many MCPs | MCP Gateway, policy, audit, service identity — see [Orchestrator vs MCP Gateway](2026-06-13-orchestrator-vs-mcp-gateway.md) |

### Where (this article's real topology)

```text
┌──────────────────────────────────────────────────────────┐
│  Human (Cursor chat)                                     │
│  "用 robinhood-trading 只读列一下我的账户"                  │
└────────────────────────────┬─────────────────────────────┘
                             ▼
┌──────────────────────────────────────────────────────────┐
│  MCP Host = Cursor Agent runtime                         │
│  - LLM chooses tool from tools/list                      │
│  - Issues tools/call                                     │
│  - Renders result (may mask account numbers per guide)   │
└────────────────────────────┬─────────────────────────────┘
                             │ stdio (local process)
                             ▼
┌──────────────────────────────────────────────────────────┐
│  mcp-remote (local bridge)                               │
│  - Owns OAuth (callback 127.0.0.1:3334)                   │
│  - Speaks Streamable HTTP to vendor                      │
│  - Caches tokens under ~/.mcp-auth/ (never commit)       │
└────────────────────────────┬─────────────────────────────┘
                             │ HTTPS Streamable HTTP
                             ▼
┌──────────────────────────────────────────────────────────┐
│  Robinhood Trading MCP                                   │
│  https://agent.robinhood.com/mcp/trading                 │
│  - Tool registry (get_*, review_*, place_*, …)           │
│  - Broker authz (agentic_allowed, account scope)         │
└────────────────────────────┬─────────────────────────────┘
                             ▼
┌──────────────────────────────────────────────────────────┐
│  Brokerage backends (accounts, portfolio, orders)        │
└──────────────────────────────────────────────────────────┘
```

This is **Pattern 1 (Agent → MCP)** from XingAI's MCP architecture notes, with a **local OAuth/transport adapter** inserted because the host and vendor disagree on OAuth clients. That adapter is not theoretical — without it, authorize fails on `/oauth/error`.

---

## 1. What MCP is — and what it is not

### MCP is

| Concept | Meaning in practice |
|---------|---------------------|
| **Host** | The agent product (Cursor, Claude Desktop, your gateway) that loads MCP clients |
| **Client** | Protocol peer inside the host that maintains a session with one server |
| **Server** | Process or URL exposing tools (here: Robinhood's hosted HTTP MCP) |
| **Tool** | Named operation with JSON Schema args + description the model reads |
| **Transport** | How messages move: **stdio** (subprocess) or **Streamable HTTP** (remote URL) |

A successful session roughly:

1. Connect / initialize  
2. `tools/list` → catalog of tools the model may choose  
3. Model emits a tool call  
4. Host runs `tools/call`  
5. Result returns as tool output → next LLM turn  

### MCP is not

- **Not** an orchestrator for multi-agent workflows (that is an Orchestrator Agent — [prior article](2026-06-13-orchestrator-vs-mcp-gateway.md))
- **Not** your product policy — if the vendor exposes `place_equity_order`, MCP will happily call it when the model asks
- **Not** a substitute for IAM — OAuth proves *who connected*; tools still decide *what that principal may do*
- **Not** automatically fail-closed for writes — broker docs may allow "trade without asking me again"

Enterprise mistake: "We added MCP, so we're governed." You added **capability**. Governance is a layer you put on purpose.

---

## 2. The real path: from Chinese prompt to account list

Concrete XingAI session (read-only):

> User: `用 robinhood-trading 只读列一下我的账户`

### Step A — Intent stays in natural language

The host does not parse "只读" as a protocol flag. The **model** is instructed (system prompt + user text) to prefer read tools. MCP itself has no global "read-only mode" switch in this setup.

Lesson: **safety language in prompts is advisory.** Real enforcement is which tools you call and which product gates you wrap around writes.

### Step B — Host selects the MCP server

Cursor maps the conversation to the configured server `robinhood-trading` in `~/.cursor/mcp.json`. In the working XingAI config, that entry is **not** a raw URL. It is a **command** that starts `mcp-remote`, which then dials Robinhood over HTTP.

Why that matters: the host's native HTTP MCP OAuth used `redirect_uri=http://localhost:8787/callback`. Robinhood rejected it. The bridge runs its **own** OAuth with `http://127.0.0.1:3334/oauth/callback`, which the vendor accepts in this flow.

### Step C — Session + catalog

Once authenticated, the client has a live session. The agent (or host tooling layer) has already obtained `tools/list`. The model sees descriptions such as:

- `get_accounts` — list brokerage accounts; buying power is **not** reliable here → use `get_portfolio`
- `place_equity_order` — real money; requires an `agentic_allowed` account  

Those descriptions are **part of the control plane**. Vendors encode operational rules in prose the LLM reads. That is powerful and fragile: the model may ignore them under pressure; your product must not rely on description text alone for irreversible actions.

### Step D — `tools/call` get_accounts

Arguments: empty object (this tool needs none).

Response shape (simplified):

```json
{
  "data": {
    "accounts": [
      {
        "account_number": "…",
        "brokerage_account_type": "individual",
        "nickname": "Agentic",
        "is_default": false,
        "agentic_allowed": true
      }
    ]
  },
  "guide": "Mask account numbers when presenting… Flag agentic_allowed when choosing a trade account…"
}
```

Two payloads matter:

1. **`data`** — facts for the next reasoning step  
2. **`guide`** — vendor instructions to the *agent host* on how to present and choose  

This is a production MCP pattern you should copy for internal servers: return **machine data + presentation/policy guide**, so every host (Cursor, Claude, your gateway) behaves consistently without hardcoding UI rules in each client.

### Step E — Presentation layer in the host

XingAI's agent masked account numbers (`••••7900`) and sorted default → agentic → other → IRA per the guide. The full `account_number` stayed available for subsequent tool calls (masking in URLs would break upgrade links).

Lesson: **MCP results are not always user-facing copy.** Hosts often transform them. Enterprise audit must log the **tool call + raw result**, not only the chat paraphrase.

### Step F — Follow-on call: portfolio

User: `看 Agentic 账户组合`

Agent calls `get_portfolio` with the **full** Agentic `account_number`. Result: cash-only balance, zero equity — another read path, same session, still no write.

That multi-step flow is the normal MCP loop: **list → choose identifier → call specialized tool**. The model carries identifiers across turns; you must treat those identifiers as sensitive.

---

## 3. Transports: why stdio and HTTP both appear

| Transport | Where it shows up in this case | Properties |
|-----------|--------------------------------|------------|
| **stdio** | Cursor ↔ `mcp-remote` child process | Local, simple, good for bridges and private tools |
| **Streamable HTTP** | `mcp-remote` ↔ `agent.robinhood.com` | Remote SaaS; needs correct HTTP semantics; OAuth at this edge |

A common failure mode: configuring the host with `"type": "sse"` or assuming "URL = always works." Robinhood's server expects **streamable HTTP**. Wrong transport → mysterious connect failures that look like auth bugs.

**Architectural takeaway:** Hosted vendor MCP ⇒ your enterprise host often needs an **adapter process** (stdio bridge, gateway sidecar) that normalizes transport + OAuth. That adapter is a first-class component — version-pin it (`mcp-remote@0.1.37`), document its ports, and treat its token cache as secrets.

---

## 4. OAuth is where "real MCP" usually breaks

### The conflict

| Actor | Redirect it wants |
|-------|-------------------|
| Cursor native HTTP MCP client | `http://localhost:8787/callback` |
| Working Robinhood + mcp-remote flow | `http://127.0.0.1:3334/oauth/callback` |

Robinhood authorize failed with Cursor's client (`/oauth/error`). There was **no** `mcp.json` knob to override `redirect_uri`.

### Secondary traps (also real)

1. **Dead listener** — user finishes browser login after the local callback server exited → `ERR_CONNECTION_REFUSED`. Auth codes are **one-time**; you cannot refresh the success URL.  
2. **`localhost` vs `127.0.0.1`** — on macOS, `localhost` may be IPv6 `::1` while the bridge binds IPv4. Prefer explicit `127.0.0.1`.  
3. **Token cache location** — e.g. `~/.mcp-auth/mcp-remote-0.1.37/`. Pin the bridge version so cache paths stay stable; never commit tokens.

### Enterprise pattern

Treat OAuth as a **compatibility matrix**:

```text
(Host OAuth client) × (Vendor allowlisted redirect) × (Transport)
```

When any cell mismatches, you need either:

- Vendor allowlists the host's redirect, or  
- A **local OAuth-owning bridge** (this case), or  
- Your **MCP Gateway** performs OAuth / token exchange and agents use **service identity** downstream

Consumer "Connect in Settings" only works when that matrix already aligns. Enterprise platforms should assume it does **not**.

---

## 5. Tool catalog design: read, review, place

Robinhood's catalog teaches a three-tier write discipline that enterprise MCPs should copy:

| Tier | Examples | Side effect |
|------|----------|-------------|
| **Read** | `get_accounts`, `get_portfolio`, `get_equity_quotes` | None (or negligible) |
| **Simulate** | `review_equity_order`, `review_option_order` | None — returns quotes/alerts |
| **Mutate** | `place_equity_order`, `place_option_order`, watchlist writes | Real money / state change |

### Why `review_*` exists

A naive agent jumps to `place_*`. Production agents should:

1. `get_equity_tradability` / portfolio checks  
2. `review_*` — surface PDT, buying power, halts  
3. Human confirm in the **product** UI or chat  
4. `place_*` only after confirm  

MCP can *encourage* this in tool descriptions ("Always confirm with the user before calling"). It cannot *force* a hostile or confused model. That is why XingAI **ADR-028** sits above the protocol: G1 human confirm, G6 Agentic-only, G7 audit — product law, not vendor courtesy.

### Authorization inside tools: `agentic_allowed`

`get_accounts` returns `agentic_allowed` **per account, relative to this agent connection**. In the live XingAI session: one nicknamed Agentic account was `true`; default individual, managed, and Roth were `false` for this agent.

Meaning for architects:

- OAuth ≠ "all linked accounts are writable"  
- Tool results carry **caller-relative** flags  
- Trade tools must reject non-agentic accounts server-side (defense in depth)  
- Product UX must steer the user to the writable account explicitly  

This is the same idea as scoped tool lists in an MCP Gateway: **visibility and executability are filtered per principal.**

---

## 6. Who decides? Model, host, server, product

Four decision layers fire on every call:

```text
1. MODEL   — picks a tool name + args from natural language
2. HOST    — may refuse to send tools/call (UI confirm, allowlist)
3. SERVER  — validates schema, OAuth session, broker rules
4. PRODUCT — XingAI gates (ADR-028) before enabling write skills / UI
```

| Layer | Robinhood case example |
|-------|------------------------|
| Model | Chooses `get_accounts` after "只读列账户" |
| Host | Cursor runs the call; no extra confirm for reads |
| Server | Returns accounts; would reject place on non-agentic |
| Product | Docs + skills forbid auto-place; require review |

**Demo teams stop at layer 1–3.** Enterprise decision systems design layer 4 deliberately. Otherwise you inherit the vendor's risk posture — including optional "don't ask again" auto-trade.

Related: [Agent Governance Reference Architecture](2026-07-05-agent-governance-reference-architecture.md) — authority, policy, approval, provenance, audit planes map cleanly onto MCP write paths.

---

## 7. Mapping the case to enterprise MCP strategy

| Building block | In this case | Enterprise generalization |
|----------------|--------------|---------------------------|
| Domain MCP | Robinhood hosted Trading MCP | GitHub / Jira / SAP / internal Claims MCP |
| Host | Cursor | IDE, Teams bot, internal agent runtime |
| Bridge / adapter | `mcp-remote` | Sidecar that fixes OAuth + transport |
| Gateway | Shipped same day as this article, see update below — a local proxy in front of `mcp-remote`, enforcing gates in code | Required when N MCPs + central policy, **or** — this case's actual reason — when the write-tool blast radius alone justifies code enforcement even for one MCP |
| Orchestrator | Not used (single agent chat) | Multi-agent planning *above* tools |
| Product gates | ADR-028 G1–G7 — three of seven now run as code in the gateway (G1/G6/G7), two more wired same day (G2/G3); see update below | Per-domain execution gates + Decision Ledger |

**Do not** build an "Orchestration MCP" to replace the orchestrator ([prior article](2026-06-13-orchestrator-vs-mcp-gateway.md)). **Do** expect a bridge when consuming third-party hosted MCPs from mainstream hosts.

Strategic options for a product company (also in Invest AI wiki):

1. **Consumer path** — document how users connect host + vendor MCP (skill = setup + safety checklist)  
2. **Product path** — your app computes decisions; user executes via their own MCP (you don't custody)  
3. **Platform path** — your Broker/Domain MCP behind your gateway (Alpaca paper, internal systems)

Robinhood MCP is path 1 today, with path 2 gates documented so Invest AI never confuses "MCP can" with "product will."

---

## 8. Checklist: what "understand MCP" means for a senior review

After this case, an architect should be able to answer:

- [ ] Where is the **host**, **bridge**, and **server** in our diagram?  
- [ ] Which **transport** each hop uses?  
- [ ] Who owns **OAuth** and which **redirect_uri** is allowlisted?  
- [ ] Where are **tokens** stored, and are they gitignored?  
- [ ] Which tools are **read / review / mutate**?  
- [ ] What **server-side** flags constrain writes (`agentic_allowed`, scopes)?  
- [ ] What **product gates** sit above MCP for irreversible actions?  
- [ ] Do tool responses include a **`guide`** for consistent host behavior?  
- [ ] If we add a second MCP tomorrow, do we need a **gateway** already?

If any box is blank, the integration is still a demo.

---

## 9. Failure modes worth teaching

| Symptom | Layer | Lesson |
|---------|-------|--------|
| `/oauth/error` | Host OAuth client vs vendor | Redirect allowlists are part of MCP design |
| Callback connection refused | Bridge lifecycle | OAuth listeners must stay up for the full browser round-trip |
| Model calls `place_*` after "just looking" | Prompt-only safety | Need host/product deny path |
| Place fails on default account | Server authz | Writable subset ≠ all accounts from `get_accounts` |
| Works in Claude, fails in Cursor | Host matrix | Same MCP URL ≠ same OAuth client |
| Token folder churn after upgrade | Bridge versioning | Pin `mcp-remote` (or sidecar) versions |

---

## Update (later the same day): the gateway this article said wasn't needed

Section 7's table above originally read "Gateway: Not used (single MCP)." That was true for the topology this article documents — direct `Cursor → mcp-remote → Robinhood` — and it changed the same day, which is worth walking through, because the reasoning is the more useful artifact than the correction itself.

Section 6 already named the gap: "MCP can *encourage* [the review-before-place discipline] in tool descriptions. It cannot *force* a hostile or confused model." Section 8's checklist even asked the right question — *"If we add a second MCP tomorrow, do we need a gateway already?"* — but framed the gateway as a multi-MCP concern. The actual trigger turned out narrower: **one MCP, with a write-tool blast radius large enough that prompt-level discipline (`common-prompts.md` asking the agent to `review_*` before `place_*`) wasn't a gate, it was a request.**

[`xingai-robinhood-mcp` ADR-001](https://github.com/xingaiapp/xingai-robinhood-mcp/blob/main/docs/adr/001-mcp-gateway-proxy.md) shipped a local MCP gateway proxy: clients connect to it instead of `agent.robinhood.com` directly. Reads pass straight through. Writes (`place_*`/`cancel_*`) are evaluated against ADR-028's seven gates before forwarding — three self-contained enough to build without touching another repo (**G1** human confirm via a pending-approval queue, **G6** agentic-account-only checked against the upstream's own flag, **G7** one audit-ledger row per write attempt, written before the forwarding decision). The other four reject by name and fail closed — `"G3 data freshness not wired — fail-closed"` — rather than silently passing. **No write order could succeed through the gateway that morning, by construction**, which is the correct default for a tool sitting in front of a real brokerage account, not a partial rollout bug.

By the end of the same day, two more gates were real: **G3** ([ADR-002](https://github.com/xingaiapp/xingai-robinhood-mcp/blob/main/docs/adr/002-g3-data-freshness-wired.md)) and **G2** ([ADR-003](https://github.com/xingaiapp/xingai-robinhood-mcp/blob/main/docs/adr/003-g2-step-up-wired-single-user.md), deliberately scoped to reuse Invest AI's existing single-admin OTP flow rather than build general per-user step-up auth for a gateway with exactly one operator). G4/G5 remain fail-closed — no trade can still succeed — but two of the four "needs another repo's infrastructure" gates turned out to need only wiring, since Invest AI had already shipped the underlying endpoints before this article's topology diagram was drawn.

**The corrected generalization:** don't reach for "gateway" only at N-MCP central-policy scale. Reach for it whenever the answer to "can a description in `tools/list` actually stop a write?" is no, and the write is expensive enough that a request isn't a good enough gate. That can be true at N=1.

---

## Learn the auth protocol next

Architecture above assumes OAuth already worked. For a beginner-to-industry walkthrough of discovery, PKCE, JWT verification, scopes, and review→execute — plus a build-from-scratch lab — see:

- [MCP Auth from Robinhood (concepts)](../guides/2026-07-12-mcp-oauth-auth-deep-dive.md)
- [OAuth 2.1 + PKCE MCP lab](../guides/2026-07-12-mcp-oauth-pkce-lab.md)

---

## Summary

MCP in production is not "paste a URL." In the Robinhood + Cursor case it is:

1. A **protocol loop** (list → call → reason)  
2. A **transport split** (stdio bridge + HTTP server)  
3. An **OAuth compatibility problem** solved by a local bridge  
4. A **tool catalog** that separates read, review, and real money  
5. **Server-side account flags** that shrink write blast radius  
6. A **product gate layer** (ADR-028) that refuses to inherit optional auto-execute  

That stack is what enterprise architects should replicate — and harden — when the next vendor ships "our MCP."

---

## Disclaimer

Informational and educational only. Not investment, legal, or brokerage advice. Robinhood Agentic Trading and the Trading MCP are Robinhood products; their terms and disclosures control. XingAI accepts no responsibility for trading outcomes or third-party MCP misuse. You can lose money.

**Official Robinhood overview:** https://robinhood.com/us/en/support/articles/agentic-trading-overview/

---

**Author:** Xing Wang, AI Architect  
**Brand:** XingAI  
**Published:** July 11, 2026  
**Tags:** architecture, enterprise, mcp, oauth, agents, tool-gateway, governance  
**Related:** [Orchestrator vs MCP Gateway](2026-06-13-orchestrator-vs-mcp-gateway.md) · [Agent Governance](2026-07-05-agent-governance-reference-architecture.md) · [xingai-robinhood-mcp](https://github.com/xingaiapp/xingai-robinhood-mcp)
