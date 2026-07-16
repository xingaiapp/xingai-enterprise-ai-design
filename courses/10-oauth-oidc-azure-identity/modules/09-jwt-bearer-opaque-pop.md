# Module 09: JWT, Bearer, Opaque, and PoP Tokens

Chinese: [09-jwt-bearer-opaque-pop.zh.md](09-jwt-bearer-opaque-pop.zh.md) | Prev: [08-oauth-token-types](08-oauth-token-types.md) | [Course hub](../README.md) | Next: [10-scope-role-business-authorization](10-scope-role-business-authorization.md)

## 5W + How

- **What:** JWT is a format. Bearer is a usage model. Opaque tokens need introspection. PoP binds a token to a proof key.
- **Why:** wrong identity boundaries create confused-deputy and silent over-privilege failures.
- **Who:** API gateways, MCP servers, mobile clients.
- **When:** choose format by revocation, size, and sender-constraint needs.
- **Where:** identity and policy sit at trust boundaries between clients, IdPs, APIs, and tools.
- **How:** learn the vocabulary, draw the sequence, implement the minimal check, then fail closed on mismatch.

## Diagram

```mermaid
flowchart LR
    JWT[JWT self-contained claims] --> Val[Local JWKS validate]
    Opaque[Opaque reference] --> Intro[Introspection]
    PoP[PoP bound key] --> Proof[Proof of possession]
```

## Code

```python
def needs_introspection(token_format: str) -> bool:
    return token_format == "opaque"
assert needs_introspection("opaque") and not needs_introspection("jwt")
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

- Wiki: [JWT, Bearer, Opaque, and PoP Tokens](https://github.com/xingaiapp/xingai-ai-learning-wiki/blob/main/wiki/concepts/oauth-oidc-azure-identity/09-jwt-bearer-opaque-pop.md)
- Lab: [OAuth 2.1 + PKCE MCP](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-pkce-lab.md)
- Deep dive: [MCP OAuth auth](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-auth-deep-dive.md)
- Specs: [OAuth 2.1](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-v2-1-13) · [OIDC Core](https://openid.net/specs/openid-connect-core-1_0.html) · [Entra ID docs](https://learn.microsoft.com/entra/identity/)
