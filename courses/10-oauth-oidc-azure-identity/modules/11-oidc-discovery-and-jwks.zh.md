# 模块 11: OIDC Discovery 与 JWKS

English: [11-oidc-discovery-and-jwks.md](11-oidc-discovery-and-jwks.md) | 上一课: [10-scope-role-business-authorization](10-scope-role-business-authorization.zh.md) | [课程主页](../README.zh.md) | 下一课: [12-microsoft-entra-id-architecture](12-microsoft-entra-id-architecture.zh.md)

## 5W + How

- **What（是什么）:** Discovery 文档公布端点与能力；JWKS 公布用于校验 JWT 签名的密钥。
- **Why（为什么）:** 错误的身份边界会导致混淆代理与静默越权。
- **Who（谁）:** 资源服务器、网关、本地校验 JWT 的客户端。
- **When（何时）:** 校验 issuer、缓存并轮换 JWKS，切勿硬编码签名密钥。
- **Where（何处）:** 身份与策略位于客户端、IdP、API 与工具之间的信任边界。
- **How（怎么做）:** 先掌握词汇与时序，实现最小校验，不匹配则失败关闭。

## 图示

```mermaid
sequenceDiagram
    participant RS as Resource Server
    participant Disc as openid-configuration
    participant JWKS as jwks_uri
    RS->>Disc: fetch metadata
    Disc-->>RS: issuer, token, jwks_uri
    RS->>JWKS: fetch keys
    JWKS-->>RS: signing keys
```

## 代码

```python
meta = {"issuer": "https://login.example", "jwks_uri": "https://login.example/keys"}
assert meta["issuer"].startswith("https://") and "jwks_uri" in meta
```

## 故障模式

- 把登录成功当成授权通过。
- 把错误类型的令牌发给错误的受众。
- 跳过 PKCE、state、nonce 或精确回调校验。
- 只把业务策略写在提示词或 UI 可见性里。

## 练习

1. 分别以初学者、工程师、架构师、CTO 深度讲解本模块。
2. 为自己的技术栈补一条最可能故障的负向测试。
3. 对照 wiki 批判页，记下一条 Missing / Needs evidence。

## 来源

- Wiki: [OIDC Discovery 与 JWKS](https://github.com/xingaiapp/xingai-ai-learning-wiki/blob/main/wiki/concepts/oauth-oidc-azure-identity/11-oidc-discovery-and-jwks.zh.md)
- 实验: [OAuth 2.1 + PKCE MCP](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-pkce-lab.md)
- 深读: [MCP OAuth 认证](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-auth-deep-dive.md)
- 规范: [OAuth 2.1](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-v2-1-13) · [OIDC Core](https://openid.net/specs/openid-connect-core-1_0.html) · [Entra ID 文档](https://learn.microsoft.com/entra/identity/)
