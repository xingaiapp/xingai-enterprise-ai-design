# Module 01: Identity and Access Management Overview

Chinese: [01-iam-overview.zh.md](01-iam-overview.zh.md) | [Course hub](../README.md) | Next: [02-authentication-vs-authorization](02-authentication-vs-authorization.md)

## 5W + How

- **What:** IAM is the control plane for who actors are and what they may do across apps, APIs, and agents.
- **Why:** wrong identity boundaries create confused-deputy and silent over-privilege failures.
- **Who:** identities, credentials, policies, directories, auditors.
- **When:** before building any protected API, MCP server, or multi-tenant product.
- **Where:** identity and policy sit at trust boundaries between clients, IdPs, APIs, and tools.
- **How:** learn the vocabulary, draw the sequence, implement the minimal check, then fail closed on mismatch.

## Diagram

```mermaid
flowchart TB
    Id[Identities] --> AuthN[Authentication]
    AuthN --> Tok[Tokens / sessions]
    Tok --> AuthZ[Authorization]
    AuthZ --> Res[Resources / tools]
    AuthZ --> Audit[Audit trail]
```

## Code

```python
# who are you?
assert "authn" != "authz"
roles = {"reader": {"doc.read"}, "editor": {"doc.read", "doc.write"}}
def may(role: str, action: str) -> bool:
    return action in roles.get(role, set())
assert may("reader", "doc.read") and not may("reader", "doc.write")
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

- Wiki: [Identity and Access Management Overview](https://github.com/xingaiapp/xingai-ai-learning-wiki/blob/main/wiki/concepts/oauth-oidc-azure-identity/01-iam-overview.md)
- Lab: [OAuth 2.1 + PKCE MCP](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-pkce-lab.md)
- Deep dive: [MCP OAuth auth](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-auth-deep-dive.md)
- Specs: [OAuth 2.1](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-v2-1-13) · [OIDC Core](https://openid.net/specs/openid-connect-core-1_0.html) · [Entra ID docs](https://learn.microsoft.com/entra/identity/)
