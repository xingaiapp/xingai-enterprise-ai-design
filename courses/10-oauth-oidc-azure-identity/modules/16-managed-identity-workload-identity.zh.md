# 模块 16: 托管标识与工作负载标识

English: [16-managed-identity-workload-identity.md](16-managed-identity-workload-identity.md) | 上一课: [15-azure-api-management-security](15-azure-api-management-security.zh.md) | [课程主页](../README.zh.md) | 下一课: [17-on-behalf-of-flow](17-on-behalf-of-flow.zh.md)

## 5W + How

- **What（是什么）:** 托管/工作负载标识让 Azure（或 Kubernetes）工作负载在不内嵌密钥的情况下获取令牌。
- **Why（为什么）:** 错误的身份边界会导致混淆代理与静默越权。
- **Who（谁）:** 平台/SRE、服务所有者。
- **When（何时）:** 服务到 Azure 资源访问；优先于长期客户端密钥。
- **Where（何处）:** 身份与策略位于客户端、IdP、API 与工具之间的信任边界。
- **How（怎么做）:** 先掌握词汇与时序，实现最小校验，不匹配则失败关闭。

## 图示

```mermaid
flowchart LR
    Workload --> MI[Managed / workload identity]
    MI --> Entra
    Entra --> Token[Access token]
    Token --> AzureRes[Key Vault / Storage / API]
```

## 代码

```python
preferred = "managed_identity_or_federated_credential"
assert preferred.startswith("managed")
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

- Wiki: [托管标识与工作负载标识](https://github.com/xingaiapp/xingai-ai-learning-wiki/blob/main/wiki/concepts/oauth-oidc-azure-identity/16-managed-identity-workload-identity.zh.md)
- 实验: [OAuth 2.1 + PKCE MCP](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-pkce-lab.md)
- 深读: [MCP OAuth 认证](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-auth-deep-dive.md)
- 规范: [OAuth 2.1](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-v2-1-13) · [OIDC Core](https://openid.net/specs/openid-connect-core-1_0.html) · [Entra ID 文档](https://learn.microsoft.com/entra/identity/)
