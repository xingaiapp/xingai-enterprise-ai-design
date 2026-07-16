# Module 19: API Keys and PATs

Chinese: [19-api-keys-and-pats.zh.md](19-api-keys-and-pats.zh.md) | Prev: [18-session-and-cookie-security](18-session-and-cookie-security.md) | [Course hub](../README.md) | Next: [20-oauth-oidc-vs-saml](20-oauth-oidc-vs-saml.md)

## 5W + How

- **What:** API keys and personal access tokens are shared secrets. They authenticate a caller but usually lack user consent UX and fine-grained OAuth scopes.
- **Why:** wrong identity boundaries create confused-deputy and silent over-privilege failures.
- **Who:** internal automation, partner integrations under contract.
- **When:** prefer OAuth for third-party and user-delegated access; keys only with rotation, scoped vaults, and monitoring.
- **Where:** identity and policy sit at trust boundaries between clients, IdPs, APIs, and tools.
- **How:** learn the vocabulary, draw the sequence, implement the minimal check, then fail closed on mismatch.

## Diagram

```mermaid
flowchart LR
    Key[API key / PAT] --> Secret[Shared secret risk]
    OAuth[OAuth + PKCE] --> Consent[Consent + scopes + revocation]
```

## Code

```python
def prefer_oauth(third_party: bool, user_delegated: bool) -> str:
    return "oauth" if third_party or user_delegated else "key_with_controls"
assert prefer_oauth(True, False) == "oauth" 
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

- Wiki: [API Keys and PATs](https://github.com/xingaiapp/xingai-ai-learning-wiki/blob/main/wiki/concepts/oauth-oidc-azure-identity/19-api-keys-and-pats.md)
- Lab: [OAuth 2.1 + PKCE MCP](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-pkce-lab.md)
- Deep dive: [MCP OAuth auth](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-auth-deep-dive.md)
- Specs: [OAuth 2.1](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-v2-1-13) · [OIDC Core](https://openid.net/specs/openid-connect-core-1_0.html) · [Entra ID docs](https://learn.microsoft.com/entra/identity/)
