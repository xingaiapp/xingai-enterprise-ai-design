# Module 13: Azure App Registration

Chinese: [13-azure-app-registration.zh.md](13-azure-app-registration.zh.md) | Prev: [12-microsoft-entra-id-architecture](12-microsoft-entra-id-architecture.md) | [Course hub](../README.md) | Next: [14-msal-integration](14-msal-integration.md)

## 5W + How

- **What:** App registration defines client IDs, redirect URIs, API scopes/roles, and credentials for Entra apps.
- **Why:** wrong identity boundaries create confused-deputy and silent over-privilege failures.
- **Who:** app owners, platform engineers.
- **When:** before issuing tokens to a new web, SPA, API, or MCP resource.
- **Where:** identity and policy sit at trust boundaries between clients, IdPs, APIs, and tools.
- **How:** learn the vocabulary, draw the sequence, implement the minimal check, then fail closed on mismatch.

## Diagram

```mermaid
flowchart LR
    Reg[App registration] --> Redirect[Redirect URIs]
    Reg --> Expose[Expose API scopes]
    Reg --> Creds[Secrets / certificates / federated creds]
```

## Code

```python
registration = {
  "client_id": "uuid",
  "redirect_uris": ["https://app.example/callback"],
  "expose_scopes": ["access_as_user"],
}
assert registration["redirect_uris"][0].startswith("https://")
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

- Wiki: [Azure App Registration](https://github.com/xingaiapp/xingai-ai-learning-wiki/blob/main/wiki/concepts/oauth-oidc-azure-identity/13-azure-app-registration.md)
- Lab: [OAuth 2.1 + PKCE MCP](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-pkce-lab.md)
- Deep dive: [MCP OAuth auth](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-auth-deep-dive.md)
- Specs: [OAuth 2.1](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-v2-1-13) · [OIDC Core](https://openid.net/specs/openid-connect-core-1_0.html) · [Entra ID docs](https://learn.microsoft.com/entra/identity/)
