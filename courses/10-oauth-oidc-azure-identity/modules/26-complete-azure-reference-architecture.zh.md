# 模块 26: 完整 Azure 参考架构

English: [26-complete-azure-reference-architecture.md](26-complete-azure-reference-architecture.md) | 上一课: [25-common-errors-and-troubleshooting](25-common-errors-and-troubleshooting.zh.md) | [课程主页](../README.zh.md)

## 5W + How

- **What（是什么）:** 参考形态：Entra（员工或 External ID）+ MSAL 客户端 + APIM 边缘 + 托管标识 API + 可选双墙授权的 MCP 资源服务器。
- **Why（为什么）:** 错误的身份边界会导致混淆代理与静默越权。
- **Who（谁）:** 企业架构师、评估 Azure 中心化栈的 CTO。
- **When（何时）:** 教学与 Azure 标准环境——不含 APIM 的可移植 OIDC/OAuth 设计仍然有效。
- **Where（何处）:** 身份与策略位于客户端、IdP、API 与工具之间的信任边界。
- **How（怎么做）:** 先掌握词汇与时序，实现最小校验，不匹配则失败关闭。

## 图示

```mermaid
flowchart TB
    User --> MSAL[MSAL app]
    MSAL --> Entra[Entra ID / External ID]
    MSAL --> APIM[APIM JWT validate]
    APIM --> API[API + business policy]
    API --> MI[Managed identity]
    MI --> Azure[Key Vault / data]
    Host[MCP Host] --> Entra
    Host --> MCP[MCP Server resource]
    MCP --> Policy[Scope + business policy + ledger]
```

## 代码

```python
components = ["entra", "msal", "apim_optional", "api_policy", "managed_identity", "mcp_two_wall"]
assert "mcp_two_wall" in components and "apim_optional" in components
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

- Wiki: [完整 Azure 参考架构](https://github.com/xingaiapp/xingai-ai-learning-wiki/blob/main/wiki/concepts/oauth-oidc-azure-identity/26-complete-azure-reference-architecture.zh.md)
- 实验: [OAuth 2.1 + PKCE MCP](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-pkce-lab.md)
- 深读: [MCP OAuth 认证](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-auth-deep-dive.md)
- 规范: [OAuth 2.1](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-v2-1-13) · [OIDC Core](https://openid.net/specs/openid-connect-core-1_0.html) · [Entra ID 文档](https://learn.microsoft.com/entra/identity/)
