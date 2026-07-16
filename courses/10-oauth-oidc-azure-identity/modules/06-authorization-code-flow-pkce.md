# Module 06: Authorization Code Flow with PKCE

Chinese: [06-authorization-code-flow-pkce.zh.md](06-authorization-code-flow-pkce.zh.md) | Prev: [05-id-token-vs-access-token](05-id-token-vs-access-token.md) | [Course hub](../README.md) | Next: [07-state-nonce-and-pkce](07-state-nonce-and-pkce.md)

## 5W + How

- **What:** Public clients exchange an authorization code for tokens using PKCE so intercepted codes cannot be redeemed.
- **Why:** wrong identity boundaries create confused-deputy and silent over-privilege failures.
- **Who:** browser/mobile/SPA clients, authorization server, redirect URI owners.
- **When:** default interactive user login for modern public clients; avoid implicit flow.
- **Where:** identity and policy sit at trust boundaries between clients, IdPs, APIs, and tools.
- **How:** learn the vocabulary, draw the sequence, implement the minimal check, then fail closed on mismatch.

## Diagram

```mermaid
sequenceDiagram
    participant C as Client
    participant AS as AS
    C->>C: code_verifier + challenge
    C->>AS: authorize + challenge
    AS-->>C: authorization code
    C->>AS: code + verifier
    AS-->>C: tokens
```

## Code

```python
import hashlib, base64, secrets
verifier = secrets.token_urlsafe(32)
digest = hashlib.sha256(verifier.encode()).digest()
challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
assert len(verifier) >= 32 and challenge != verifier
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

- Wiki: [Authorization Code Flow with PKCE](https://github.com/xingaiapp/xingai-ai-learning-wiki/blob/main/wiki/concepts/oauth-oidc-azure-identity/06-authorization-code-flow-pkce.md)
- Lab: [OAuth 2.1 + PKCE MCP](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-pkce-lab.md)
- Deep dive: [MCP OAuth auth](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-auth-deep-dive.md)
- Specs: [OAuth 2.1](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-v2-1-13) · [OIDC Core](https://openid.net/specs/openid-connect-core-1_0.html) · [Entra ID docs](https://learn.microsoft.com/entra/identity/)
