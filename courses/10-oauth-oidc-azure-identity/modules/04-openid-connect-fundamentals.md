# Module 04: OpenID Connect Fundamentals

Chinese: [04-openid-connect-fundamentals.zh.md](04-openid-connect-fundamentals.zh.md) | Prev: [03-oauth-2-fundamentals](03-oauth-2-fundamentals.md) | [Course hub](../README.md) | Next: [05-id-token-vs-access-token](05-id-token-vs-access-token.md)

## 5W + How

- **What:** OIDC is an identity layer on OAuth: it authenticates the user and returns an ID Token to the client.
- **Why:** wrong identity boundaries create confused-deputy and silent over-privilege failures.
- **Who:** relying party, end user, OpenID provider.
- **When:** user sign-in and single sign-on; pair with OAuth when APIs need access tokens.
- **Where:** identity and policy sit at trust boundaries between clients, IdPs, APIs, and tools.
- **How:** learn the vocabulary, draw the sequence, implement the minimal check, then fail closed on mismatch.

## Diagram

```mermaid
flowchart LR
    OAuth[OAuth authorization] --> OIDC[OIDC identity]
    OIDC --> IDT[ID Token to client]
    OAuth --> AT[Access Token to API]
```

## Code

```python
oidc = {"uses_oauth": True, "adds": ["id_token", "userinfo", "discovery"]}
assert oidc["uses_oauth"] and "id_token" in oidc["adds"]
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

- Wiki: [OpenID Connect Fundamentals](https://github.com/xingaiapp/xingai-ai-learning-wiki/blob/main/wiki/concepts/oauth-oidc-azure-identity/04-openid-connect-fundamentals.md)
- Lab: [OAuth 2.1 + PKCE MCP](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-pkce-lab.md)
- Deep dive: [MCP OAuth auth](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-auth-deep-dive.md)
- Specs: [OAuth 2.1](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-v2-1-13) · [OIDC Core](https://openid.net/specs/openid-connect-core-1_0.html) · [Entra ID docs](https://learn.microsoft.com/entra/identity/)
