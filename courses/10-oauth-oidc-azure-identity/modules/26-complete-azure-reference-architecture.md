# Module 26: Complete Azure Reference Architecture

Chinese: [26-complete-azure-reference-architecture.zh.md](26-complete-azure-reference-architecture.zh.md) | Prev: [25-common-errors-and-troubleshooting](25-common-errors-and-troubleshooting.md) | [Course hub](../README.md)

## 5W + How

- **What:** A reference shape: Entra (workforce or External ID) + MSAL clients + APIM edge + APIs with managed identity + optional MCP resource server with two-wall authz.
- **Why:** wrong identity boundaries create confused-deputy and silent over-privilege failures.
- **Who:** enterprise architects, CTOs evaluating Azure-centric stacks.
- **When:** teaching and Azure-standard shops — portable OIDC/OAuth designs remain valid without APIM.
- **Where:** identity and policy sit at trust boundaries between clients, IdPs, APIs, and tools.
- **How:** learn the vocabulary, draw the sequence, implement the minimal check, then fail closed on mismatch.

## Diagram

```mermaid
flowchart TB
    User --> MSAL[MSAL app]
    MSAL --> Entra[Entra ID / External ID]
    MSAL --> APIM[APIM JWT validate]
    APIM --> API[API + business policy]
    API --> MI[Managed identity]
    MI --> Azure[Key Vault / data]
    Host[MCP Host] --> Entra
    Host --> MCP[MCP Server resource]
    MCP --> Policy[Scope + business policy + ledger]
```

## Code

```python
components = ["entra", "msal", "apim_optional", "api_policy", "managed_identity", "mcp_two_wall"]
assert "mcp_two_wall" in components and "apim_optional" in components
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

- Wiki: [Complete Azure Reference Architecture](https://github.com/xingaiapp/xingai-ai-learning-wiki/blob/main/wiki/concepts/oauth-oidc-azure-identity/26-complete-azure-reference-architecture.md)
- Lab: [OAuth 2.1 + PKCE MCP](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-pkce-lab.md)
- Deep dive: [MCP OAuth auth](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-auth-deep-dive.md)
- Specs: [OAuth 2.1](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-v2-1-13) · [OIDC Core](https://openid.net/specs/openid-connect-core-1_0.html) · [Entra ID docs](https://learn.microsoft.com/entra/identity/)
