# Module 25: Common Errors and Troubleshooting

Chinese: [25-common-errors-and-troubleshooting.zh.md](25-common-errors-and-troubleshooting.zh.md) | Prev: [24-security-best-practices](24-security-best-practices.md) | [Course hub](../README.md) | Next: [26-complete-azure-reference-architecture](26-complete-azure-reference-architecture.md)

## 5W + How

- **What:** Most auth bugs are redirect mismatch, wrong audience, expired tokens, clock skew, missing PKCE, or confusing ID vs access tokens.
- **Why:** wrong identity boundaries create confused-deputy and silent over-privilege failures.
- **Who:** on-call engineers, integrators.
- **When:** when login or API 401/403 appears — debug claims before rewriting the app.
- **Where:** identity and policy sit at trust boundaries between clients, IdPs, APIs, and tools.
- **How:** learn the vocabulary, draw the sequence, implement the minimal check, then fail closed on mismatch.

## Diagram

```mermaid
flowchart TB
    E401[401/403] --> Q1{Token present?}
    Q1 -->|no| Login[Fix login / acquire]
    Q1 -->|yes| Q2{iss/aud/exp ok?}
    Q2 -->|no| Claims[Fix validation]
    Q2 -->|yes| Q3{scope/policy?}
    Q3 -->|no| AuthZ[Fix authorization]
```

## Code

```python
def classify(status: int, aud_ok: bool) -> str:
    if status == 401 and not aud_ok:
        return "audience_or_issuer"
    if status == 403:
        return "authorization"
    return "other"
assert classify(401, False) == "audience_or_issuer" 
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

- Wiki: [Common Errors and Troubleshooting](https://github.com/xingaiapp/xingai-ai-learning-wiki/blob/main/wiki/concepts/oauth-oidc-azure-identity/25-common-errors-troubleshooting.md)
- Lab: [OAuth 2.1 + PKCE MCP](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-pkce-lab.md)
- Deep dive: [MCP OAuth auth](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-auth-deep-dive.md)
- Specs: [OAuth 2.1](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-v2-1-13) · [OIDC Core](https://openid.net/specs/openid-connect-core-1_0.html) · [Entra ID docs](https://learn.microsoft.com/entra/identity/)
