---
title: MCP Auth from Robinhood — OAuth 2.1, PKCE, and Token Verification for Beginners
author: Xing Wang
date: 2026-07-12
tags: [mcp, oauth, pkce, jwt, security, education, agents, robinhood, human-in-the-loop]
description: A step-by-step education guide to MCP authentication using Robinhood Agentic Trading MCP as the teaching case — discovery, PKCE, token storage, JWT checks, scopes, and review-before-execute.
---

# MCP Auth from Robinhood: OAuth 2.1 / PKCE / Token Verification (Beginner Deep Dive)

**中文：** [中文版](2026-07-12-mcp-oauth-auth-deep-dive.zh.md)  
**Hands-on lab (next):** [Build an OAuth 2.1 + PKCE MCP project from scratch](2026-07-12-mcp-oauth-pkce-lab.md)  
**Architecture sibling:** [How MCP Works in Production](../articles/2026-07-11-mcp-in-production-robinhood-case.md)

---

## Why this guide exists

On 27 May 2026 Robinhood announced Agentic access for AI agents — trading and credit features with security controls and activity logs. Agentic Trading uses a **separate Agentic Account**. Users need a healthy personal brokerage account, then complete Agentic Account setup during Trading MCP connect. Auth and onboarding are expected on **desktop**.

If a service can spend money or place orders, auth design decides whether it is a useful tool or a disaster waiting to happen.

This guide uses **Robinhood’s official MCP** as a teaching case and walks industry-standard pieces:

- Protected Resource Metadata + Authorization Server Metadata  
- Why desktop apps must not embed `client_secret`  
- What PKCE actually blocks  
- Loopback OAuth callbacks  
- Storing and refreshing tokens safely  
- How an MCP server verifies tokens  
- How to implement auth in your own MCP  
- How to stop agents from running high-risk tools without confirmation  

URLs and parameters here are **illustrative**. Always prefer live metadata and vendor docs over hard-coded values from this article.

**Not investment advice.** Do not wire real money to an unaudited home-built MCP. XingAI’s implementation notes live in [xingai-robinhood-mcp](https://github.com/xingaiapp/xingai-robinhood-mcp).

---

## 1. What MCP auth must solve

Four roles:

| Role | Job |
|------|-----|
| Resource Owner | The user who owns the account |
| MCP Client | Claude, ChatGPT, Cursor, or your agent host |
| MCP Server / Resource Server | Tools, resources, prompts |
| Authorization Server | Login, consent, tokens |

Core question:

> How does the agent prove the user authorized it — without ever holding the user’s password?

### 1.1 Anti-pattern: passwords in MCP config

Putting `ROBINHOOD_USERNAME` / `ROBINHOOD_PASSWORD` in client env gives near-full account power, no fine-grained scopes, no per-agent revoke, and weak audit. Correct shape: config holds only the MCP URL; the user logs in on the vendor’s site; the client keeps a **short-lived, limited** token.

---

## 2. Three different credentials

| Credential | Lifetime | Use |
|------------|----------|-----|
| Authorization Code | Seconds; usually one-shot | Exchange for tokens |
| Access Token | Minutes–hours | Call the MCP server |
| Refresh Token | Longer | Get a new access token |

Never send the authorization code as `Authorization: Bearer …`. Exchange first.

---

## 3. Discovery is two layers

```text
Protected Resource Metadata
  → “Which authorization server issues tokens for me?”

Authorization Server Metadata
  → authorize / token / register / PKCE methods
```

Typical path: unauthenticated MCP call → **401** with `WWW-Authenticate: Bearer resource_metadata="…"` → GET that URL → follow `authorization_servers[0]` to `/.well-known/oauth-authorization-server`.

Validate HTTPS (except local demos), issuer match, required endpoints, and **S256** in `code_challenge_methods_supported`. Treat metadata hosts as untrusted input — SSRF, private IPs, and evil redirects are real failure modes. MCP security guidance calls this out explicitly.

---

## 4. PKCE replaces client secrets on public clients

Anything in a desktop install can be reverse-engineered. A fixed `client_secret` in the binary is public.

PKCE: generate a high-entropy `code_verifier`, send `code_challenge = BASE64URL(SHA256(verifier))` at authorize time, send the verifier at token time. Server recomputes and compares with a constant-time check.

Stolen `?code=` without the original verifier fails exchange. MCP security expects clients to implement PKCE.

---

## 5. State, redirect URI, loopback callback

- **State** — CSRF / callback mix-up; store before authorize; compare on return.  
- **Redirect URI** — exact string match (`localhost` ≠ `127.0.0.1`). Loopback HTTP is OK for desktop; remote redirects need HTTPS.  
- Prefer an OS-assigned free port when the AS allows dynamic loopback registration.  
- Do not log raw codes.

---

## 6. Token exchange: HTTP 200 is not enough

Validate: status, JSON, non-empty `access_token`, `token_type=bearer`, sane `expires_in`. Community reports in mid-2026 showed empty tokens being persisted while the UI looked “logged in.”

---

## 7. Storage, refresh, concurrency

Prefer OS keychain / secret manager over plaintext `tokens.json`. Convert `expires_in` → `expires_at` and refresh ~60s early.

On refresh rotation, keep the new refresh token when returned. On **401**, refresh and retry **once**; second 401 clears tokens and forces re-auth. Use a lock (or distributed lock) so five parallel calls do not burn a rotated refresh token.

---

## 8. MCP JSON-RPC errors

HTTP 200 can still carry `"error": { "code": -32602, … }`. Check `jsonrpc`, then `result` vs `error`.

---

## 9. Scopes and audience

Prefer fine scopes (`portfolio.read`, `orders.review`, `orders.place`) over one fat `trading` scope. Least privilege: read before write; review before place. Verify granted scopes after exchange.

Bind tokens to a **resource** / **aud**. The trading MCP must reject tokens minted for another API.

---

## 10. Server-side verification

1. Missing Bearer → **401** + `WWW-Authenticate` pointing at resource metadata.  
2. JWT → JWKS signature + `iss` / `aud` / `exp` / algorithm. Never disable signature verify.  
3. Opaque → introspection; require `active: true`.  
4. Enforce scopes per tool (403 `insufficient_scope`).  

Publish your own Protected Resource Metadata document.

---

## 11. Dynamic client registration

Public clients often register with `token_endpoint_auth_method=none`. Persist registration against the issuer.

---

## 12. Review → confirm → execute

OAuth answers “did the user authorize this client?” It does **not** answer “did the user approve this specific trade?”

Split high-risk tools:

```text
review_*  → preview only
user confirms the summary
place_*   → review_id (+ confirmation / idempotency) only
```

Reviews expire and are single-use. Execute must not accept mutable symbol/qty. Use **Idempotency-Key**. Prompt text is a request; **server policy** is the gate — same lesson as XingAI [ADR-028](https://github.com/xingaiapp/xingai-invest-ai/blob/main/docs/adr/028-robinhood-mcp-execution-gates.md) and the [robinhood-mcp gateway](https://github.com/xingaiapp/xingai-robinhood-mcp).

---

## 13. No token passthrough

Do not forward the user’s access token to third parties. Validate locally, then call downstream with a service credential or a proper token exchange.

---

## 14. Logging, revoke, audit

Never log tokens, codes, or verifiers. Logout should revoke then delete local secrets. Audit who called which tool, with which decision and review id — not the bearer string.

---

## 15. Defense in depth in the Robinhood case

Public materials emphasize a **separate Agentic Account**, permission separation, visible activity, and revoke-from-vendor. That is the pattern worth copying even when you are not building a broker.

---

## 16. Ten beginner mistakes

| Mistake | Fix |
|---------|-----|
| Password in MCP config | OAuth |
| Client secret in desktop app | PKCE public client |
| Skip state | Random state + constant-time compare |
| Guess token URL | Metadata discovery |
| Trust HTTP 200 alone | Field-level token validation |
| Log tokens | Redact |
| Long-lived access tokens | Short access + refresh |
| Infinite 401 retry | One refresh retry |
| Mutable params after review | Freeze in review_id |
| Skip audience check | Verify `aud` |

---

## 17. One diagram

```text
Discovery → OAuth 2.1 → PKCE → short access token
  → minimal scopes → resource/audience bind
  → isolated agent account → review + user confirm
  → limits / idempotency / audit → revoke anytime
```

One line:

> Don’t give the agent a password. Don’t give a token unlimited power. Don’t treat one login as approval for every high-risk action. Make every execution limited, confirmable, auditable, and revocable.

Before trusting a new MCP with money or production data, ask: why passwords instead of OAuth? what are aud/scope? what can a leaked token do? is there per-action confirm? can I revoke at the vendor?

---

## Next

Build a runnable Auth Server + MCP Server + Client with a **simulated** portfolio (no real broker):

→ [Build an OAuth 2.1 + PKCE MCP project from scratch](2026-07-12-mcp-oauth-pkce-lab.md)

Production topology and fail-closed gateway:

→ [How MCP Works in Production](../articles/2026-07-11-mcp-in-production-robinhood-case.md)

---

## Disclaimer

Code here is educational. It omits HSM, full SSRF defenses, DPoP, distributed locks, and compliance audit systems. Robinhood endpoints and scopes change — follow live metadata. Informational only; not investment, legal, or security advice. You own how you use it.

---

**Author:** Xing Wang  
**Published:** 2026-07-12  
**Tags:** mcp, oauth, pkce, jwt, security, education
