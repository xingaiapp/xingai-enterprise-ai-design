# Module 22: MCP Server Authentication and Authorization

Chinese: [22-mcp-server-authn-authz.zh.md](22-mcp-server-authn-authz.zh.md) | Prev: [21-microsoft-entra-external-id](21-microsoft-entra-external-id.md) | [Course hub](../README.md) | Next: [23-logging-monitoring-and-auditing](23-logging-monitoring-and-auditing.md)

## 5W + How

- **What:** An MCP server is a resource server: authenticate the caller, authorize each tool, bind audience, and audit.
- **Why:** wrong identity boundaries create confused-deputy and silent over-privilege failures.
- **Who:** MCP server authors, host/client developers, security.
- **When:** any remote MCP exposing tools; combine OAuth wall with business policy wall.
- **Where:** identity and policy sit at trust boundaries between clients, IdPs, APIs, and tools.
- **How:** learn the vocabulary, draw the sequence, implement the minimal check, then fail closed on mismatch.

## Diagram

```mermaid
sequenceDiagram
    participant Host
    participant AS as Auth Server
    participant MCP as MCP Server
    Host->>AS: OAuth + PKCE + resource
    AS-->>Host: audience-bound AT
    Host->>MCP: tool call + bearer
    MCP->>MCP: verify + policy + audit
```

## Code

```python
def mcp_allow(aud_ok: bool, scope_ok: bool, policy_ok: bool) -> bool:
    return aud_ok and scope_ok and policy_ok
assert not mcp_allow(True, True, False)
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

- Wiki: [MCP Server Authentication and Authorization](https://github.com/xingaiapp/xingai-ai-learning-wiki/blob/main/wiki/concepts/oauth-oidc-azure-identity/22-mcp-server-authn-authz.md)
- Lab: [OAuth 2.1 + PKCE MCP](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-pkce-lab.md)
- Deep dive: [MCP OAuth auth](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-auth-deep-dive.md)
- Specs: [OAuth 2.1](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-v2-1-13) · [OIDC Core](https://openid.net/specs/openid-connect-core-1_0.html) · [Entra ID docs](https://learn.microsoft.com/entra/identity/)
