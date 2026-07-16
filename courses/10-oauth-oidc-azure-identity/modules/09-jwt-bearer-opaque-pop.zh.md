# 模块 09: JWT、Bearer、不透明令牌与 PoP

English: [09-jwt-bearer-opaque-pop.md](09-jwt-bearer-opaque-pop.md) | 上一课: [08-oauth-token-types](08-oauth-token-types.zh.md) | [课程主页](../README.zh.md) | 下一课: [10-scope-role-business-authorization](10-scope-role-business-authorization.zh.md)

## 5W + How

- **What（是什么）:** JWT 是格式；Bearer 是使用模型；不透明令牌需 introspection；PoP 把令牌绑定到证明密钥。
- **Why（为什么）:** 错误的身份边界会导致混淆代理与静默越权。
- **Who（谁）:** API 网关、MCP Server、移动客户端。
- **When（何时）:** 按吊销、体积与发送方约束需求选择格式。
- **Where（何处）:** 身份与策略位于客户端、IdP、API 与工具之间的信任边界。
- **How（怎么做）:** 先掌握词汇与时序，实现最小校验，不匹配则失败关闭。

## 图示

```mermaid
flowchart LR
    JWT[JWT self-contained claims] --> Val[Local JWKS validate]
    Opaque[Opaque reference] --> Intro[Introspection]
    PoP[PoP bound key] --> Proof[Proof of possession]
```

## 代码

```python
def needs_introspection(token_format: str) -> bool:
    return token_format == "opaque"
assert needs_introspection("opaque") and not needs_introspection("jwt")
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

- Wiki: [JWT、Bearer、不透明令牌与 PoP](https://github.com/xingaiapp/xingai-ai-learning-wiki/blob/main/wiki/concepts/oauth-oidc-azure-identity/09-jwt-bearer-opaque-pop.zh.md)
- 实验: [OAuth 2.1 + PKCE MCP](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-pkce-lab.md)
- 深读: [MCP OAuth 认证](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-auth-deep-dive.md)
- 规范: [OAuth 2.1](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-v2-1-13) · [OIDC Core](https://openid.net/specs/openid-connect-core-1_0.html) · [Entra ID 文档](https://learn.microsoft.com/entra/identity/)
