# 模块 14: MSAL 集成

English: [14-msal-integration.md](14-msal-integration.md) | 上一课: [13-azure-app-registration](13-azure-app-registration.zh.md) | [课程主页](../README.zh.md) | 下一课: [15-azure-api-management-security](15-azure-api-management-security.zh.md)

## 5W + How

- **What（是什么）:** MSAL 库实现微软身份的 OIDC/OAuth 流、令牌缓存与账户选择。
- **Why（为什么）:** 错误的身份边界会导致混淆代理与静默越权。
- **Who（谁）:** 基于 Entra 的前后端工程师。
- **When（何时）:** Entra 应用优先用 MSAL，而非手写授权 URL；仍需理解底层协议。
- **Where（何处）:** 身份与策略位于客户端、IdP、API 与工具之间的信任边界。
- **How（怎么做）:** 先掌握词汇与时序，实现最小校验，不匹配则失败关闭。

## 图示

```mermaid
sequenceDiagram
    participant App
    participant MSAL
    participant Entra
    App->>MSAL: login / acquireToken
    MSAL->>Entra: authorize + token
    Entra-->>MSAL: tokens
    MSAL-->>App: access token for API
```

## 代码

```python
strategy = ["silent_cache", "interactive_if_needed"]
assert strategy[0] == "silent_cache" 
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

- Wiki: [MSAL 集成](https://github.com/xingaiapp/xingai-ai-learning-wiki/blob/main/wiki/concepts/oauth-oidc-azure-identity/14-msal-integration.zh.md)
- 实验: [OAuth 2.1 + PKCE MCP](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-pkce-lab.md)
- 深读: [MCP OAuth 认证](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-auth-deep-dive.md)
- 规范: [OAuth 2.1](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-v2-1-13) · [OIDC Core](https://openid.net/specs/openid-connect-core-1_0.html) · [Entra ID 文档](https://learn.microsoft.com/entra/identity/)
