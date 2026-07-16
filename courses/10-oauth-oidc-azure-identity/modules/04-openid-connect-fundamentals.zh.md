# 模块 04: OpenID Connect 基础

English: [04-openid-connect-fundamentals.md](04-openid-connect-fundamentals.md) | 上一课: [03-oauth-2-fundamentals](03-oauth-2-fundamentals.zh.md) | [课程主页](../README.zh.md) | 下一课: [05-id-token-vs-access-token](05-id-token-vs-access-token.zh.md)

## 5W + How

- **What（是什么）:** OIDC 是 OAuth 上的身份层：认证用户并向客户端返回 ID Token。
- **Why（为什么）:** 错误的身份边界会导致混淆代理与静默越权。
- **Who（谁）:** 依赖方、终端用户、OpenID 提供方。
- **When（何时）:** 用户登录与 SSO；需要访问 API 时再配合 OAuth 拿 Access Token。
- **Where（何处）:** 身份与策略位于客户端、IdP、API 与工具之间的信任边界。
- **How（怎么做）:** 先掌握词汇与时序，实现最小校验，不匹配则失败关闭。

## 图示

```mermaid
flowchart LR
    OAuth[OAuth authorization] --> OIDC[OIDC identity]
    OIDC --> IDT[ID Token to client]
    OAuth --> AT[Access Token to API]
```

## 代码

```python
oidc = {"uses_oauth": True, "adds": ["id_token", "userinfo", "discovery"]}
assert oidc["uses_oauth"] and "id_token" in oidc["adds"]
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

- Wiki: [OpenID Connect 基础](https://github.com/xingaiapp/xingai-ai-learning-wiki/blob/main/wiki/concepts/oauth-oidc-azure-identity/04-openid-connect-fundamentals.zh.md)
- 实验: [OAuth 2.1 + PKCE MCP](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-pkce-lab.md)
- 深读: [MCP OAuth 认证](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-auth-deep-dive.md)
- 规范: [OAuth 2.1](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-v2-1-13) · [OIDC Core](https://openid.net/specs/openid-connect-core-1_0.html) · [Entra ID 文档](https://learn.microsoft.com/entra/identity/)
