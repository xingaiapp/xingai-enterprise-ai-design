# Module 17: On-Behalf-Of Flow

Chinese: [17-on-behalf-of-flow.zh.md](17-on-behalf-of-flow.zh.md) | Prev: [16-managed-identity-workload-identity](16-managed-identity-workload-identity.md) | [Course hub](../README.md) | Next: [18-session-and-cookie-security](18-session-and-cookie-security.md)

## 5W + How

- **What:** OBO lets a middle-tier API exchange a user token for a new token to call a downstream API as that user.
- **Why:** wrong identity boundaries create confused-deputy and silent over-privilege failures.
- **Who:** multi-API product backends, MCP gateways calling user-scoped APIs.
- **When:** when the middle tier must preserve user identity downstream — not for pure app-only calls.
- **Where:** identity and policy sit at trust boundaries between clients, IdPs, APIs, and tools.
- **How:** learn the vocabulary, draw the sequence, implement the minimal check, then fail closed on mismatch.

## Diagram

```mermaid
sequenceDiagram
    participant C as Client
    participant Mid as Middle API
    participant AS as Entra
    participant Down as Downstream API
    C->>Mid: user access token
    Mid->>AS: OBO exchange
    AS-->>Mid: downstream token
    Mid->>Down: call as user
```

## Code

```python
def needs_obo(call_as_user: bool, middle_tier: bool) -> bool:
    return call_as_user and middle_tier
assert needs_obo(True, True) and not needs_obo(False, True)
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

- Wiki: [On-Behalf-Of Flow](https://github.com/xingaiapp/xingai-ai-learning-wiki/blob/main/wiki/concepts/oauth-oidc-azure-identity/17-on-behalf-of-flow.md)
- Lab: [OAuth 2.1 + PKCE MCP](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-pkce-lab.md)
- Deep dive: [MCP OAuth auth](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-auth-deep-dive.md)
- Specs: [OAuth 2.1](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-v2-1-13) · [OIDC Core](https://openid.net/specs/openid-connect-core-1_0.html) · [Entra ID docs](https://learn.microsoft.com/entra/identity/)
