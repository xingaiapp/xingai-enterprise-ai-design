# 模块 18: 会话与 Cookie 安全

English: [18-session-and-cookie-security.md](18-session-and-cookie-security.md) | 上一课: [17-on-behalf-of-flow](17-on-behalf-of-flow.zh.md) | [课程主页](../README.zh.md) | 下一课: [19-api-keys-and-pats](19-api-keys-and-pats.zh.md)

## 5W + How

- **What（是什么）:** 应用会话不是 OAuth 令牌。Cookie 需要 Secure、HttpOnly、SameSite 与轮换规则。
- **Why（为什么）:** 错误的身份边界会导致混淆代理与静默越权。
- **Who（谁）:** Web 应用开发者。
- **When（何时）:** OIDC 登录后的浏览器应用；会话 Cookie 与 Access Token 存放分离。
- **Where（何处）:** 身份与策略位于客户端、IdP、API 与工具之间的信任边界。
- **How（怎么做）:** 先掌握词汇与时序，实现最小校验，不匹配则失败关闭。

## 图示

```mermaid
flowchart TB
    OIDC[OIDC login] --> Session[App session cookie]
    Session --> API[Backend uses server-side token store]
    Browser -.->|no long-lived AT in JS| X[Avoid]
```

## 代码

```python
cookie = {"Secure": True, "HttpOnly": True, "SameSite": "Lax"}
assert cookie["HttpOnly"] and cookie["Secure"]
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

- Wiki: [会话与 Cookie 安全](https://github.com/xingaiapp/xingai-ai-learning-wiki/blob/main/wiki/concepts/oauth-oidc-azure-identity/18-session-and-cookie-security.zh.md)
- 实验: [OAuth 2.1 + PKCE MCP](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-pkce-lab.md)
- 深读: [MCP OAuth 认证](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-auth-deep-dive.md)
- 规范: [OAuth 2.1](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-v2-1-13) · [OIDC Core](https://openid.net/specs/openid-connect-core-1_0.html) · [Entra ID 文档](https://learn.microsoft.com/entra/identity/)
