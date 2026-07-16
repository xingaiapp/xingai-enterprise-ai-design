# 模块 12: Microsoft Entra ID 架构

English: [12-microsoft-entra-id-architecture.md](12-microsoft-entra-id-architecture.md) | 上一课: [11-oidc-discovery-and-jwks](11-oidc-discovery-and-jwks.zh.md) | [课程主页](../README.zh.md) | 下一课: [13-azure-app-registration](13-azure-app-registration.zh.md)

## 5W + How

- **What（是什么）:** Entra ID 是微软云目录与身份平台：租户、应用、用户、组、条件访问。
- **Why（为什么）:** 错误的身份边界会导致混淆代理与静默越权。
- **Who（谁）:** Azure/企业架构师、IdP 管理员。
- **When（何时）:** 组织以微软身份为标准时；把概念映射到可移植的 OIDC 术语。
- **Where（何处）:** 身份与策略位于客户端、IdP、API 与工具之间的信任边界。
- **How（怎么做）:** 先掌握词汇与时序，实现最小校验，不匹配则失败关闭。

## 图示

```mermaid
flowchart TB
    Tenant[Entra tenant] --> Apps[App registrations]
    Tenant --> Users[Users / groups]
    Apps --> Tokens[OIDC/OAuth tokens]
    Users --> CA[Conditional Access]
```

## 代码

```python
mapping = {"entra_app": "oidc_client_or_resource", "tenant": "issuer_authority"}
assert mapping["tenant"] == "issuer_authority" 
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

- Wiki: [Microsoft Entra ID 架构](https://github.com/xingaiapp/xingai-ai-learning-wiki/blob/main/wiki/concepts/oauth-oidc-azure-identity/12-microsoft-entra-id-architecture.zh.md)
- 实验: [OAuth 2.1 + PKCE MCP](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-pkce-lab.md)
- 深读: [MCP OAuth 认证](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-auth-deep-dive.md)
- 规范: [OAuth 2.1](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-v2-1-13) · [OIDC Core](https://openid.net/specs/openid-connect-core-1_0.html) · [Entra ID 文档](https://learn.microsoft.com/entra/identity/)
