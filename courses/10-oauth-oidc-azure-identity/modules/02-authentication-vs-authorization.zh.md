# 模块 02: 认证与授权

English: [02-authentication-vs-authorization.md](02-authentication-vs-authorization.md) | 上一课: [01-iam-overview](01-iam-overview.zh.md) | [课程主页](../README.zh.md) | 下一课: [03-oauth-2-fundamentals](03-oauth-2-fundamentals.zh.md)

## 5W + How

- **What（是什么）:** 认证回答你是谁；授权回答通过认证后你能做什么。
- **Why（为什么）:** 错误的身份边界会导致混淆代理与静默越权。
- **Who（谁）:** 用户、服务、IdP、资源服务器、策略所有者。
- **When（何时）:** 每一个受保护边界；切勿把登录成功当成业务权限。
- **Where（何处）:** 身份与策略位于客户端、IdP、API 与工具之间的信任边界。
- **How（怎么做）:** 先掌握词汇与时序，实现最小校验，不匹配则失败关闭。

## 图示

```mermaid
sequenceDiagram
    participant U as User
    participant C as Client
    participant IdP as IdP
    participant API as Resource
    U->>IdP: authenticate
    IdP-->>C: identity proof
    C->>API: request + token
    API->>API: authorize action
```

## 代码

```python
def authorize(authenticated: bool, scope: set[str], action: str) -> bool:
    if not authenticated:
        return False
    return action in scope
assert authorize(True, {"orders.read"}, "orders.read")
assert not authorize(True, {"orders.read"}, "orders.write")
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

- Wiki: [认证与授权](https://github.com/xingaiapp/xingai-ai-learning-wiki/blob/main/wiki/concepts/oauth-oidc-azure-identity/02-authentication-vs-authorization.zh.md)
- 实验: [OAuth 2.1 + PKCE MCP](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-pkce-lab.md)
- 深读: [MCP OAuth 认证](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-auth-deep-dive.md)
- 规范: [OAuth 2.1](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-v2-1-13) · [OIDC Core](https://openid.net/specs/openid-connect-core-1_0.html) · [Entra ID 文档](https://learn.microsoft.com/entra/identity/)
