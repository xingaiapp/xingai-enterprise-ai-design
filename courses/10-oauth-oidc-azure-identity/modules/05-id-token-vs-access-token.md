# Module 05: ID Token vs Access Token

Chinese: [05-id-token-vs-access-token.zh.md](05-id-token-vs-access-token.zh.md) | Prev: [04-openid-connect-fundamentals](04-openid-connect-fundamentals.md) | [Course hub](../README.md) | Next: [06-authorization-code-flow-pkce](06-authorization-code-flow-pkce.md)

## 5W + How

- **What:** ID Token is for the client to learn who signed in. Access Token is for the API/MCP server to authorize calls.
- **Why:** wrong identity boundaries create confused-deputy and silent over-privilege failures.
- **Who:** SPA/web clients, APIs, MCP resource servers.
- **When:** never send ID Tokens as API bearer credentials; never treat Access Tokens as login sessions alone.
- **Where:** identity and policy sit at trust boundaries between clients, IdPs, APIs, and tools.
- **How:** learn the vocabulary, draw the sequence, implement the minimal check, then fail closed on mismatch.

## Diagram

```mermaid
flowchart TB
    Login[User login] --> IDT[ID Token to Client session]
    Login --> AT[Access Token to API / MCP]
    IDT -.->|do not use as API bearer| X[Wrong]
    AT --> API[Resource Server validates aud/iss/exp]
```

## Code

```python
def route_token(kind: str) -> str:
    return {"id_token": "client", "access_token": "resource_server"}[kind]
assert route_token("id_token") == "client"
assert route_token("access_token") == "resource_server" 
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

- Wiki: [ID Token vs Access Token](https://github.com/xingaiapp/xingai-ai-learning-wiki/blob/main/wiki/concepts/oauth-oidc-azure-identity/05-id-token-vs-access-token.md)
- Lab: [OAuth 2.1 + PKCE MCP](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-pkce-lab.md)
- Deep dive: [MCP OAuth auth](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-auth-deep-dive.md)
- Specs: [OAuth 2.1](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-v2-1-13) · [OIDC Core](https://openid.net/specs/openid-connect-core-1_0.html) · [Entra ID docs](https://learn.microsoft.com/entra/identity/)
