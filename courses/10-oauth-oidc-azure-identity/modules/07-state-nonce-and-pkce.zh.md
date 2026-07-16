# 模块 07: state、nonce 与 PKCE

English: [07-state-nonce-and-pkce.md](07-state-nonce-and-pkce.md) | 上一课: [06-authorization-code-flow-pkce](06-authorization-code-flow-pkce.zh.md) | [课程主页](../README.zh.md) | 下一课: [08-oauth-token-types](08-oauth-token-types.zh.md)

## 5W + How

- **What（是什么）:** state 把回调绑定到浏览器会话（防 CSRF）；nonce 把 ID Token 绑定到本次登录；PKCE 把授权码绑定到客户端。
- **Why（为什么）:** 错误的身份边界会导致混淆代理与静默越权。
- **Who（谁）:** OIDC 客户端、安全评审。
- **When（何时）:** 每一次交互式 OIDC 登录；任一校验缺失则失败关闭。
- **Where（何处）:** 身份与策略位于客户端、IdP、API 与工具之间的信任边界。
- **How（怎么做）:** 先掌握词汇与时序，实现最小校验，不匹配则失败关闭。

## 图示

```mermaid
flowchart LR
    state[state to callback CSRF] --> OK[Accept login]
    nonce[nonce to ID Token binding] --> OK
    pkce[PKCE to code binding] --> OK
```

## 代码

```python
checks = {"state_match": True, "nonce_match": True, "pkce_ok": True}
assert all(checks.values())
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

- Wiki: [state、nonce 与 PKCE](https://github.com/xingaiapp/xingai-ai-learning-wiki/blob/main/wiki/concepts/oauth-oidc-azure-identity/07-state-nonce-and-pkce.zh.md)
- 实验: [OAuth 2.1 + PKCE MCP](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-pkce-lab.md)
- 深读: [MCP OAuth 认证](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-auth-deep-dive.md)
- 规范: [OAuth 2.1](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-v2-1-13) · [OIDC Core](https://openid.net/specs/openid-connect-core-1_0.html) · [Entra ID 文档](https://learn.microsoft.com/entra/identity/)
