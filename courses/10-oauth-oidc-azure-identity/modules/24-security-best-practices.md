# Module 24: Security Best Practices

Chinese: [24-security-best-practices.zh.md](24-security-best-practices.zh.md) | Prev: [23-logging-monitoring-and-auditing](23-logging-monitoring-and-auditing.md) | [Course hub](../README.md) | Next: [25-common-errors-and-troubleshooting](25-common-errors-and-troubleshooting.md)

## 5W + How

- **What:** Least privilege, short-lived tokens, PKCE, exact redirect URIs, audience checks, secret-free workloads, and fail-closed defaults.
- **Why:** wrong identity boundaries create confused-deputy and silent over-privilege failures.
- **Who:** all builders and reviewers.
- **When:** treat as a release checklist for any identity change.
- **Where:** identity and policy sit at trust boundaries between clients, IdPs, APIs, and tools.
- **How:** learn the vocabulary, draw the sequence, implement the minimal check, then fail closed on mismatch.

## Diagram

```mermaid
flowchart TB
    L[Least privilege scopes] --> S[Short TTL + rotation]
    S --> V[Validate iss/aud/exp/sig]
    V --> F[Fail closed]
```

## Code

```python
checklist = ["pkce", "exact_redirect", "aud_check", "no_id_token_as_bearer", "rotate_refresh"]
assert "aud_check" in checklist
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

- Wiki: [Security Best Practices](https://github.com/xingaiapp/xingai-ai-learning-wiki/blob/main/wiki/concepts/oauth-oidc-azure-identity/24-security-best-practices.md)
- Lab: [OAuth 2.1 + PKCE MCP](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-pkce-lab.md)
- Deep dive: [MCP OAuth auth](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-auth-deep-dive.md)
- Specs: [OAuth 2.1](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-v2-1-13) · [OIDC Core](https://openid.net/specs/openid-connect-core-1_0.html) · [Entra ID docs](https://learn.microsoft.com/entra/identity/)
