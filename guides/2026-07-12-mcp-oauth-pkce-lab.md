---
title: Build an OAuth 2.1 + PKCE MCP Project from Scratch
author: Xing Wang
date: 2026-07-12
tags: [mcp, oauth, pkce, fastapi, education, security, jwt, hands-on]
description: Hands-on lab — Authorization Server, MCP Server, and Python client with discovery, PKCE, JWT, scopes, review→execute, idempotency, and tests. Simulated portfolio only; no real broker.
---

# Build an OAuth 2.1 + PKCE MCP Project from Scratch

**中文：** [中文版](2026-07-12-mcp-oauth-pkce-lab.zh.md)  
**Concepts first:** [MCP Auth from Robinhood](2026-07-12-mcp-oauth-auth-deep-dive.md)

This lab turns the concept guide into **three runnable processes**. Auth and gates are real; the portfolio and orders are **simulated** — **no live broker**.

---

## 1. Target architecture

```text
MCP Client ──OAuth──▶ Authorization Server (:8000)
     │                      │ JWT Access Token
     └──── Bearer ────▶ MCP Server (:8001)
                              │ Scope + Policy
                              ▼
                         Mock portfolio / review / place
```

| Service | Port | Role |
|---------|------|------|
| Auth Server | 8000 | authorize, token, well-known, JWKS, revoke |
| MCP Server | 8001 | verify token, tools/list, tools/call, review→execute |
| Client | CLI | discovery, PKCE, token store, tool calls |

Drop a full tree into [xingai-enterprise-ai-pocs](https://github.com/xingaiapp/xingai-enterprise-ai-pocs) if you want a clone-and-run POC; this guide is the **industry-standard build order** and the checks that matter.

---

## 2. Layout

```text
secure-mcp-demo/
├── auth_server/   # main, models, security, storage
├── mcp_server/    # main, auth, tools, policies
├── client/        # main, oauth, discovery, token_store
├── tests/
├── keys/          # private.pem, public.pem
├── requirements.txt
└── docker-compose.yml  # optional
```

---

## 3. Bootstrap

```bash
python -m venv .venv && source .venv/bin/activate
pip install fastapi uvicorn[standard] requests httpx \
  "PyJWT[crypto]" cryptography python-multipart pydantic keyring pytest

mkdir -p keys
openssl genrsa -out keys/private.pem 2048
openssl rsa -in keys/private.pem -pubout -out keys/public.pem
```

Auth Server holds the private key. MCP Server needs **only** the public key / JWKS.

---

## 4. Authorization Server

**Models (in-memory for demo):** authorization codes, refresh tokens, client registrations. Seed `demo-desktop-client` with redirect `http://127.0.0.1:54321/callback`.

**Security:** PKCE verify with constant-time compare; RS256 access JWTs (`iss`, `sub`, `aud`, `scope`, `client_id`, short `exp`); expose JWKS.

**Endpoints:**

| Path | Purpose |
|------|---------|
| `GET /.well-known/oauth-authorization-server` | AS metadata |
| `GET /jwks.json` | Public keys |
| `POST /register` | Dynamic registration (demo: loopback redirects only) |
| `GET/POST /authorize` | Consent + one-shot code (~120s) |
| `POST /token` | code exchange + refresh **rotation** |
| `POST /revoke` | Revoke refresh |

Reject bad PKCE, reused codes, redirect mismatches. Demo user can be fixed as `demo-user-001`.

```bash
uvicorn auth_server.main:app --port 8000 --reload
```

---

## 5. MCP Server

**Auth middleware:** missing Bearer → 401 + `resource_metadata` URL; JWT via JWKS; scope checks → 403.

**Policy layer (second wall):** allowlisted symbols; max notional (e.g. $500) even when `orders.place` is granted.

**Tools:**

| Tool | Scope | Behavior |
|------|-------|----------|
| `get_portfolio` | `portfolio.read` | Mock holdings |
| `get_quote` | `quotes.read` | Mock quote |
| `review_equity_order` | `orders.review` | Preview + `review_id`, TTL, no fill |
| `place_equity_order` | `orders.place` | `review_id` + `idempotency_key` only |

Freeze order fields in the review. Mark reviews used under a lock. Idempotent retries return the same order payload.

Publish `GET /.well-known/oauth-protected-resource/mcp`.

```bash
uvicorn mcp_server.main:app --port 8001 --reload
# Unauthenticated tools/list must 401
```

---

## 6. Client

1. Discover resource metadata from 401  
2. Load AS metadata; require S256  
3. PKCE + state; browser consent; loopback callback  
4. Exchange code; reject empty access tokens; persist with `expires_at`  
5. Call `initialize` → `tools/list` → portfolio → review → require typed **`YES`** → place  

Refresh early; on 401 refresh and retry **once**.

```bash
python -m client.main
```

---

## 7. Experiments you must pass

| Experiment | Expected |
|------------|----------|
| Wrong `code_verifier` | PKCE / invalid_grant |
| Reuse authorization code | already used |
| Read-only scope calling review | 403 insufficient_scope |
| Wrong JWT `aud` | 401 |
| Replay old refresh after rotation | revoked |
| Place same review twice | 409 |
| Same idempotency key | identical result |

```bash
pytest -v
```

---

## 8. Docker caveat

Inside Compose, JWKS fetch may use `http://auth-server:8000/jwks.json`, but JWT **`iss` must stay the public issuer** clients know. Split env vars: `EXPECTED_ISSUER` vs `JWKS_URL`.

---

## 9. Path to production

1. **Read-only** until auth + audit are boring  
2. Low-risk writes (drafts, tags)  
3. Review / confirm state machine  
4. Real execution only with test accounts, limits, kill switch, idempotency, transactions  
5. Admin UI: connected agents, activity, revoke, pause  

Four layers:

```text
Identity (OAuth 2.1 + PKCE)
→ API authz (scope + audience)
→ Agent authz (profile + allowlist + limits)
→ Business authz (review + confirm + idempotency)
```

> Authorizing an agent to access a service is not the same as authorizing every high-risk action.

---

## 10. Ship checklist

**AS:** one-shot short codes, PKCE S256, exact redirects, refresh rotation, revocation, key vault, JWKS rotation, revocable consent.

**MCP:** signature + iss/aud/exp + scopes + policies; single-use reviews; no mutable execute args; idempotency; audit; no token logs.

**Client:** metadata + SSRF guard; fresh PKCE/state; no empty-token persist; secure store; one 401 retry; explicit human confirm for writes.

---

## Related

- Concepts: [MCP Auth deep dive](2026-07-12-mcp-oauth-auth-deep-dive.md)  
- Production case: [MCP in production](../articles/2026-07-11-mcp-in-production-robinhood-case.md)  
- [xingai-robinhood-mcp](https://github.com/xingaiapp/xingai-robinhood-mcp)  
- [Invest AI ADR-028](https://github.com/xingaiapp/xingai-invest-ai/blob/main/docs/adr/028-robinhood-mcp-execution-gates.md)

---

## Disclaimer

Educational mock system — not production-ready. Not investment, legal, or compliance advice. Use at your own risk.

---

**Author:** Xing Wang  
**Published:** 2026-07-12  
**Tags:** mcp, oauth, pkce, fastapi, education
