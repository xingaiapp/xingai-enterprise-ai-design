# Module 08: OAuth Token Types

Chinese: [08-oauth-token-types.zh.md](08-oauth-token-types.zh.md) | Prev: [07-state-nonce-and-pkce](07-state-nonce-and-pkce.md) | [Course hub](../README.md) | Next: [09-jwt-bearer-opaque-pop](09-jwt-bearer-opaque-pop.md)

## 5W + How

- **What:** Authorization codes, access tokens, refresh tokens, and ID tokens have different lifetimes, audiences, and storage rules.
- **Why:** wrong identity boundaries create confused-deputy and silent over-privilege failures.
- **Who:** AS operators, client developers, resource servers.
- **When:** design token storage and rotation before shipping any login.
- **Where:** identity and policy sit at trust boundaries between clients, IdPs, APIs, and tools.
- **How:** learn the vocabulary, draw the sequence, implement the minimal check, then fail closed on mismatch.

## Diagram

```mermaid
flowchart TB
    Code[Authorization code short-lived] --> AT[Access token API use]
    Code --> RT[Refresh token rotation]
    Code --> IDT[ID token client identity]
```

## Code

```python
TOKEN_RULES = {
  "authorization_code": {"store": "none", "ttl": "minutes"},
  "access_token": {"store": "memory", "ttl": "short"},
  "refresh_token": {"store": "http_only_cookie_or_secure_store", "ttl": "long+rotate"},
  "id_token": {"store": "client_session", "ttl": "short"},
}
assert TOKEN_RULES["refresh_token"]["store"].startswith("http_only")
```

## Failure Modes

- Confusing login success with authorization.
- Sending the wrong token type to the wrong audience.
- Skipping PKCE, state, nonce, or exact redirect checks.
- Encoding business policy only in prompts or UI visibility.

## Practice

1. Explain this module at beginner, engineer, architect, and CTO depth.
2. Add one negative test for the failure mode most likely in your stack.
3. Cross-check the wiki critique page and note one Missing / Needs evidence item.

## Sources

- Wiki: [OAuth Token Types](https://github.com/xingaiapp/xingai-ai-learning-wiki/blob/main/wiki/concepts/oauth-oidc-azure-identity/08-oauth-token-types.md)
- Lab: [OAuth 2.1 + PKCE MCP](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-pkce-lab.md)
- Deep dive: [MCP OAuth auth](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-auth-deep-dive.md)
- Specs: [OAuth 2.1](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-v2-1-13) · [OIDC Core](https://openid.net/specs/openid-connect-core-1_0.html) · [Entra ID docs](https://learn.microsoft.com/entra/identity/)
