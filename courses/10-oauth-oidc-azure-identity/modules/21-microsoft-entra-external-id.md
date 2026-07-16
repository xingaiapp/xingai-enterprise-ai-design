# Module 21: Microsoft Entra External ID

Chinese: [21-microsoft-entra-external-id.zh.md](21-microsoft-entra-external-id.zh.md) | Prev: [20-oauth-oidc-vs-saml](20-oauth-oidc-vs-saml.md) | [Course hub](../README.md) | Next: [22-mcp-server-authn-authz](22-mcp-server-authn-authz.md)

## 5W + How

- **What:** External ID covers customer/partner identity scenarios (CIAM) separate from workforce Entra tenants.
- **Why:** wrong identity boundaries create confused-deputy and silent over-privilege failures.
- **Who:** product CIAM owners, B2B/B2C architects.
- **When:** external users signing into a product; do not mix workforce admin tenants casually.
- **Where:** identity and policy sit at trust boundaries between clients, IdPs, APIs, and tools.
- **How:** learn the vocabulary, draw the sequence, implement the minimal check, then fail closed on mismatch.

## Diagram

```mermaid
flowchart LR
    ExtUser[Customer / partner] --> ExtID[Entra External ID]
    ExtID --> App[Product app]
    Workforce[Employees] --> WorkforceTenant[Workforce Entra]
```

## Code

```python
assert "external_id" != "workforce_tenant" 
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

- Wiki: [Microsoft Entra External ID](https://github.com/xingaiapp/xingai-ai-learning-wiki/blob/main/wiki/concepts/oauth-oidc-azure-identity/21-microsoft-entra-external-id.md)
- Lab: [OAuth 2.1 + PKCE MCP](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-pkce-lab.md)
- Deep dive: [MCP OAuth auth](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-auth-deep-dive.md)
- Specs: [OAuth 2.1](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-v2-1-13) · [OIDC Core](https://openid.net/specs/openid-connect-core-1_0.html) · [Entra ID docs](https://learn.microsoft.com/entra/identity/)
