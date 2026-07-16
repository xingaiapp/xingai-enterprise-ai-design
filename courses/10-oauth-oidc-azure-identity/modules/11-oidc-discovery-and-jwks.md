# Module 11: OIDC Discovery and JWKS

Chinese: [11-oidc-discovery-and-jwks.zh.md](11-oidc-discovery-and-jwks.zh.md) | Prev: [10-scope-role-business-authorization](10-scope-role-business-authorization.md) | [Course hub](../README.md) | Next: [12-microsoft-entra-id-architecture](12-microsoft-entra-id-architecture.md)

## 5W + How

- **What:** Discovery documents publish endpoints and capabilities. JWKS publishes keys used to verify JWT signatures.
- **Why:** wrong identity boundaries create confused-deputy and silent over-privilege failures.
- **Who:** resource servers, gateways, clients doing local JWT validation.
- **When:** validate issuer, cache JWKS with rotation, never hardcode signing keys.
- **Where:** identity and policy sit at trust boundaries between clients, IdPs, APIs, and tools.
- **How:** learn the vocabulary, draw the sequence, implement the minimal check, then fail closed on mismatch.

## Diagram

```mermaid
sequenceDiagram
    participant RS as Resource Server
    participant Disc as openid-configuration
    participant JWKS as jwks_uri
    RS->>Disc: fetch metadata
    Disc-->>RS: issuer, token, jwks_uri
    RS->>JWKS: fetch keys
    JWKS-->>RS: signing keys
```

## Code

```python
meta = {"issuer": "https://login.example", "jwks_uri": "https://login.example/keys"}
assert meta["issuer"].startswith("https://") and "jwks_uri" in meta
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

- Wiki: [OIDC Discovery and JWKS](https://github.com/xingaiapp/xingai-ai-learning-wiki/blob/main/wiki/concepts/oauth-oidc-azure-identity/11-oidc-discovery-and-jwks.md)
- Lab: [OAuth 2.1 + PKCE MCP](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-pkce-lab.md)
- Deep dive: [MCP OAuth auth](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-auth-deep-dive.md)
- Specs: [OAuth 2.1](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-v2-1-13) · [OIDC Core](https://openid.net/specs/openid-connect-core-1_0.html) · [Entra ID docs](https://learn.microsoft.com/entra/identity/)
