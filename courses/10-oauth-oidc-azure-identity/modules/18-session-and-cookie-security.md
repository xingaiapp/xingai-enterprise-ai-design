# Module 18: Session and Cookie Security

Chinese: [18-session-and-cookie-security.zh.md](18-session-and-cookie-security.zh.md) | Prev: [17-on-behalf-of-flow](17-on-behalf-of-flow.md) | [Course hub](../README.md) | Next: [19-api-keys-and-pats](19-api-keys-and-pats.md)

## 5W + How

- **What:** Application sessions are not OAuth tokens. Cookies need Secure, HttpOnly, SameSite, and rotation rules.
- **Why:** wrong identity boundaries create confused-deputy and silent over-privilege failures.
- **Who:** web app developers.
- **When:** browser apps after OIDC login; separate session cookie from access-token storage.
- **Where:** identity and policy sit at trust boundaries between clients, IdPs, APIs, and tools.
- **How:** learn the vocabulary, draw the sequence, implement the minimal check, then fail closed on mismatch.

## Diagram

```mermaid
flowchart TB
    OIDC[OIDC login] --> Session[App session cookie]
    Session --> API[Backend uses server-side token store]
    Browser -.->|no long-lived AT in JS| X[Avoid]
```

## Code

```python
cookie = {"Secure": True, "HttpOnly": True, "SameSite": "Lax"}
assert cookie["HttpOnly"] and cookie["Secure"]
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

- Wiki: [Session and Cookie Security](https://github.com/xingaiapp/xingai-ai-learning-wiki/blob/main/wiki/concepts/oauth-oidc-azure-identity/18-session-and-cookie-security.md)
- Lab: [OAuth 2.1 + PKCE MCP](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-pkce-lab.md)
- Deep dive: [MCP OAuth auth](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-auth-deep-dive.md)
- Specs: [OAuth 2.1](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-v2-1-13) · [OIDC Core](https://openid.net/specs/openid-connect-core-1_0.html) · [Entra ID docs](https://learn.microsoft.com/entra/identity/)
