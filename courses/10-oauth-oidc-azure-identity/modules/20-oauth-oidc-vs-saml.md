# Module 20: OAuth/OIDC vs SAML

Chinese: [20-oauth-oidc-vs-saml.zh.md](20-oauth-oidc-vs-saml.zh.md) | Prev: [19-api-keys-and-pats](19-api-keys-and-pats.md) | [Course hub](../README.md) | Next: [21-microsoft-entra-external-id](21-microsoft-entra-external-id.md)

## 5W + How

- **What:** SAML is XML federation focused on enterprise SSO. OIDC is JSON/JWT oriented and pairs naturally with OAuth APIs.
- **Why:** wrong identity boundaries create confused-deputy and silent over-privilege failures.
- **Who:** enterprise IdP architects.
- **When:** new greenfield APIs and SPAs → OIDC/OAuth; existing SAML IdP may remain for workforce SSO.
- **Where:** identity and policy sit at trust boundaries between clients, IdPs, APIs, and tools.
- **How:** learn the vocabulary, draw the sequence, implement the minimal check, then fail closed on mismatch.

## Diagram

```mermaid
flowchart TB
    SAML[SAML assertions] --> BrowserSSO[Workforce browser SSO]
    OIDC[OIDC ID Token] --> ModernApps[Modern apps]
    OAuth[OAuth access token] --> APIs[APIs / MCP]
```

## Code

```python
choice = {"browser_sso_legacy": "saml_or_oidc", "api_access": "oauth", "modern_login": "oidc"}
assert choice["api_access"] == "oauth" 
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

- Wiki: [OAuth/OIDC vs SAML](https://github.com/xingaiapp/xingai-ai-learning-wiki/blob/main/wiki/concepts/oauth-oidc-azure-identity/20-oauth-oidc-vs-saml.md)
- Lab: [OAuth 2.1 + PKCE MCP](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-pkce-lab.md)
- Deep dive: [MCP OAuth auth](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-auth-deep-dive.md)
- Specs: [OAuth 2.1](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-v2-1-13) · [OIDC Core](https://openid.net/specs/openid-connect-core-1_0.html) · [Entra ID docs](https://learn.microsoft.com/entra/identity/)
