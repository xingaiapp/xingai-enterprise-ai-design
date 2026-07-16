# Module 02: Authentication vs Authorization

Chinese: [02-authentication-vs-authorization.zh.md](02-authentication-vs-authorization.zh.md) | Prev: [01-iam-overview](01-iam-overview.md) | [Course hub](../README.md) | Next: [03-oauth-2-fundamentals](03-oauth-2-fundamentals.md)

## 5W + How

- **What:** Authentication answers who you are. Authorization answers what you may do after that.
- **Why:** wrong identity boundaries create confused-deputy and silent over-privilege failures.
- **Who:** users, services, IdP, resource servers, policy owners.
- **When:** every protected boundary; never treat login success as business permission.
- **Where:** identity and policy sit at trust boundaries between clients, IdPs, APIs, and tools.
- **How:** learn the vocabulary, draw the sequence, implement the minimal check, then fail closed on mismatch.

## Diagram

```mermaid
sequenceDiagram
    participant U as User
    participant C as Client
    participant IdP as IdP
    participant API as Resource
    U->>IdP: authenticate
    IdP-->>C: identity proof
    C->>API: request + token
    API->>API: authorize action
```

## Code

```python
def authorize(authenticated: bool, scope: set[str], action: str) -> bool:
    if not authenticated:
        return False
    return action in scope
assert authorize(True, {"orders.read"}, "orders.read")
assert not authorize(True, {"orders.read"}, "orders.write")
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

- Wiki: [Authentication vs Authorization](https://github.com/xingaiapp/xingai-ai-learning-wiki/blob/main/wiki/concepts/oauth-oidc-azure-identity/02-authentication-vs-authorization.md)
- Lab: [OAuth 2.1 + PKCE MCP](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-pkce-lab.md)
- Deep dive: [MCP OAuth auth](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-auth-deep-dive.md)
- Specs: [OAuth 2.1](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-v2-1-13) · [OIDC Core](https://openid.net/specs/openid-connect-core-1_0.html) · [Entra ID docs](https://learn.microsoft.com/entra/identity/)
