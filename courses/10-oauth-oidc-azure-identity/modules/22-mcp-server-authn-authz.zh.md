# 模块 22: MCP Server 认证与授权

English: [22-mcp-server-authn-authz.md](22-mcp-server-authn-authz.md) | 上一课: [21-microsoft-entra-external-id](21-microsoft-entra-external-id.zh.md) | [课程主页](../README.zh.md) | 下一课: [23-logging-monitoring-and-auditing](23-logging-monitoring-and-auditing.zh.md)

## 5W + How

- **What（是什么）:** MCP Server 是资源服务器：认证调用方、授权每个工具、绑定 audience，并审计。
- **Why（为什么）:** 错误的身份边界会导致混淆代理与静默越权。
- **Who（谁）:** MCP Server 作者、Host/Client 开发者、安全。
- **When（何时）:** 任何暴露工具的远程 MCP；组合 OAuth 墙与业务策略墙。
- **Where（何处）:** 身份与策略位于客户端、IdP、API 与工具之间的信任边界。
- **How（怎么做）:** 先掌握词汇与时序，实现最小校验，不匹配则失败关闭。

## 图示

```mermaid
sequenceDiagram
    participant Host
    participant AS as Auth Server
    participant MCP as MCP Server
    Host->>AS: OAuth + PKCE + resource
    AS-->>Host: audience-bound AT
    Host->>MCP: tool call + bearer
    MCP->>MCP: verify + policy + audit
```

## 代码

```python
def mcp_allow(aud_ok: bool, scope_ok: bool, policy_ok: bool) -> bool:
    return aud_ok and scope_ok and policy_ok
assert not mcp_allow(True, True, False)
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

- Wiki: [MCP Server 认证与授权](https://github.com/xingaiapp/xingai-ai-learning-wiki/blob/main/wiki/concepts/oauth-oidc-azure-identity/22-mcp-server-authn-authz.zh.md)
- 实验: [OAuth 2.1 + PKCE MCP](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-pkce-lab.md)
- 深读: [MCP OAuth 认证](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-auth-deep-dive.md)
- 规范: [OAuth 2.1](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-v2-1-13) · [OIDC Core](https://openid.net/specs/openid-connect-core-1_0.html) · [Entra ID 文档](https://learn.microsoft.com/entra/identity/)
