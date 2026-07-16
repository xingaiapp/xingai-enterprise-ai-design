# 模块 05: ID Token 与 Access Token

English: [05-id-token-vs-access-token.md](05-id-token-vs-access-token.md) | 上一课: [04-openid-connect-fundamentals](04-openid-connect-fundamentals.zh.md) | [课程主页](../README.zh.md) | 下一课: [06-authorization-code-flow-pkce](06-authorization-code-flow-pkce.zh.md)

## 5W + How

- **What（是什么）:** ID Token 给客户端确认登录身份；Access Token 给 API/MCP Server 做调用授权。
- **Why（为什么）:** 错误的身份边界会导致混淆代理与静默越权。
- **Who（谁）:** SPA/Web 客户端、API、MCP 资源服务器。
- **When（何时）:** 切勿把 ID Token 当 API Bearer；也勿仅用 Access Token 充当应用登录会话。
- **Where（何处）:** 身份与策略位于客户端、IdP、API 与工具之间的信任边界。
- **How（怎么做）:** 先掌握词汇与时序，实现最小校验，不匹配则失败关闭。

## 图示

```mermaid
flowchart TB
    Login[User login] --> IDT[ID Token to Client session]
    Login --> AT[Access Token to API / MCP]
    IDT -.->|do not use as API bearer| X[Wrong]
    AT --> API[Resource Server validates aud/iss/exp]
```

## 代码

```python
def route_token(kind: str) -> str:
    return {"id_token": "client", "access_token": "resource_server"}[kind]
assert route_token("id_token") == "client"
assert route_token("access_token") == "resource_server" 
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

- Wiki: [ID Token 与 Access Token](https://github.com/xingaiapp/xingai-ai-learning-wiki/blob/main/wiki/concepts/oauth-oidc-azure-identity/05-id-token-vs-access-token.zh.md)
- 实验: [OAuth 2.1 + PKCE MCP](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-pkce-lab.md)
- 深读: [MCP OAuth 认证](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-auth-deep-dive.md)
- 规范: [OAuth 2.1](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-v2-1-13) · [OIDC Core](https://openid.net/specs/openid-connect-core-1_0.html) · [Entra ID 文档](https://learn.microsoft.com/entra/identity/)
