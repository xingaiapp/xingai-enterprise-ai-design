# 模块 23: 日志、监控与审计

English: [23-logging-monitoring-and-auditing.md](23-logging-monitoring-and-auditing.md) | 上一课: [22-mcp-server-authn-authz](22-mcp-server-authn-authz.zh.md) | [课程主页](../README.zh.md) | 下一课: [24-security-best-practices](24-security-best-practices.zh.md)

## 5W + How

- **What（是什么）:** 认证日志须证明谁在何时用哪个令牌/应用做了什么，且不能泄露密钥或原始令牌。
- **Why（为什么）:** 错误的身份边界会导致混淆代理与静默越权。
- **Who（谁）:** SOC、平台、合规。
- **When（何时）:** 受监管或 Agent 工具调用的每条认证/授权决策路径。
- **Where（何处）:** 身份与策略位于客户端、IdP、API 与工具之间的信任边界。
- **How（怎么做）:** 先掌握词汇与时序，实现最小校验，不匹配则失败关闭。

## 图示

```mermaid
flowchart LR
    Event[AuthN/AuthZ event] --> Redact[Redact secrets]
    Redact --> SIEM[Monitor / alert]
    Redact --> Ledger[Immutable audit / decision ledger]
```

## 代码

```python
event = {"sub": "user-1", "action": "tool.invoke", "decision": "deny", "token": "[redacted]"}
assert event["token"] == "[redacted]"
assert event["decision"] in {"allow", "deny", "step_up"}
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

- Wiki: [日志、监控与审计](https://github.com/xingaiapp/xingai-ai-learning-wiki/blob/main/wiki/concepts/oauth-oidc-azure-identity/23-logging-monitoring-auditing.zh.md)
- 实验: [OAuth 2.1 + PKCE MCP](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-pkce-lab.md)
- 深读: [MCP OAuth 认证](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-auth-deep-dive.md)
- 规范: [OAuth 2.1](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-v2-1-13) · [OIDC Core](https://openid.net/specs/openid-connect-core-1_0.html) · [Entra ID 文档](https://learn.microsoft.com/entra/identity/)
