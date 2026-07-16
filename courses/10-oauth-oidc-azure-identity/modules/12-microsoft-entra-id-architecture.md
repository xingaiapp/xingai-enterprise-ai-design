# Module 12: Microsoft Entra ID Architecture

Chinese: [12-microsoft-entra-id-architecture.zh.md](12-microsoft-entra-id-architecture.zh.md) | Prev: [11-oidc-discovery-and-jwks](11-oidc-discovery-and-jwks.md) | [Course hub](../README.md) | Next: [13-azure-app-registration](13-azure-app-registration.md)

## 5W + How

- **What:** Entra ID is Microsoft's cloud directory and identity platform: tenants, apps, users, groups, conditional access.
- **Why:** wrong identity boundaries create confused-deputy and silent over-privilege failures.
- **Who:** Azure/enterprise architects, IdP admins.
- **When:** when the organization standardizes on Microsoft identity; map concepts to portable OIDC terms.
- **Where:** identity and policy sit at trust boundaries between clients, IdPs, APIs, and tools.
- **How:** learn the vocabulary, draw the sequence, implement the minimal check, then fail closed on mismatch.

## Diagram

```mermaid
flowchart TB
    Tenant[Entra tenant] --> Apps[App registrations]
    Tenant --> Users[Users / groups]
    Apps --> Tokens[OIDC/OAuth tokens]
    Users --> CA[Conditional Access]
```

## Code

```python
mapping = {"entra_app": "oidc_client_or_resource", "tenant": "issuer_authority"}
assert mapping["tenant"] == "issuer_authority" 
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

- Wiki: [Microsoft Entra ID Architecture](https://github.com/xingaiapp/xingai-ai-learning-wiki/blob/main/wiki/concepts/oauth-oidc-azure-identity/12-microsoft-entra-id-architecture.md)
- Lab: [OAuth 2.1 + PKCE MCP](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-pkce-lab.md)
- Deep dive: [MCP OAuth auth](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-auth-deep-dive.md)
- Specs: [OAuth 2.1](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-v2-1-13) · [OIDC Core](https://openid.net/specs/openid-connect-core-1_0.html) · [Entra ID docs](https://learn.microsoft.com/entra/identity/)
