# Module 16: Managed Identity and Workload Identity

Chinese: [16-managed-identity-workload-identity.zh.md](16-managed-identity-workload-identity.zh.md) | Prev: [15-azure-api-management-security](15-azure-api-management-security.md) | [Course hub](../README.md) | Next: [17-on-behalf-of-flow](17-on-behalf-of-flow.md)

## 5W + How

- **What:** Managed/workload identities let Azure (or Kubernetes) workloads obtain tokens without embedding secrets.
- **Why:** wrong identity boundaries create confused-deputy and silent over-privilege failures.
- **Who:** platform/SRE, service owners.
- **When:** service-to-service Azure resource access; prefer over long-lived client secrets.
- **Where:** identity and policy sit at trust boundaries between clients, IdPs, APIs, and tools.
- **How:** learn the vocabulary, draw the sequence, implement the minimal check, then fail closed on mismatch.

## Diagram

```mermaid
flowchart LR
    Workload --> MI[Managed / workload identity]
    MI --> Entra
    Entra --> Token[Access token]
    Token --> AzureRes[Key Vault / Storage / API]
```

## Code

```python
preferred = "managed_identity_or_federated_credential"
assert preferred.startswith("managed")
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

- Wiki: [Managed Identity and Workload Identity](https://github.com/xingaiapp/xingai-ai-learning-wiki/blob/main/wiki/concepts/oauth-oidc-azure-identity/16-managed-identity-workload-identity.md)
- Lab: [OAuth 2.1 + PKCE MCP](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-pkce-lab.md)
- Deep dive: [MCP OAuth auth](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-auth-deep-dive.md)
- Specs: [OAuth 2.1](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-v2-1-13) · [OIDC Core](https://openid.net/specs/openid-connect-core-1_0.html) · [Entra ID docs](https://learn.microsoft.com/entra/identity/)
