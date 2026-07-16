# Module 03: OAuth 2.0 Fundamentals

Chinese: [03-oauth-2-fundamentals.zh.md](03-oauth-2-fundamentals.zh.md) | Prev: [02-authentication-vs-authorization](02-authentication-vs-authorization.md) | [Course hub](../README.md) | Next: [04-openid-connect-fundamentals](04-openid-connect-fundamentals.md)

## 5W + How

- **What:** OAuth 2.x delegates authorization so a client can access a resource without holding the user's password.
- **Why:** wrong identity boundaries create confused-deputy and silent over-privilege failures.
- **Who:** resource owner, client, authorization server, resource server.
- **When:** API and tool access on behalf of a user or workload; not a login protocol by itself.
- **Where:** identity and policy sit at trust boundaries between clients, IdPs, APIs, and tools.
- **How:** learn the vocabulary, draw the sequence, implement the minimal check, then fail closed on mismatch.

## Diagram

```mermaid
sequenceDiagram
    participant RO as Resource Owner
    participant C as Client
    participant AS as Authorization Server
    participant RS as Resource Server
    RO->>AS: consent
    AS-->>C: access token
    C->>RS: API call + token
    RS-->>C: protected data
```

## Code

```python
ROLES = ["resource_owner", "client", "authorization_server", "resource_server"]
assert "authorization_server" in ROLES
assert "identity_provider" not in ROLES  # IdP is the OIDC layer
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

- Wiki: [OAuth 2.0 Fundamentals](https://github.com/xingaiapp/xingai-ai-learning-wiki/blob/main/wiki/concepts/oauth-oidc-azure-identity/03-oauth-2-fundamentals.md)
- Lab: [OAuth 2.1 + PKCE MCP](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-pkce-lab.md)
- Deep dive: [MCP OAuth auth](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-auth-deep-dive.md)
- Specs: [OAuth 2.1](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-v2-1-13) · [OIDC Core](https://openid.net/specs/openid-connect-core-1_0.html) · [Entra ID docs](https://learn.microsoft.com/entra/identity/)
