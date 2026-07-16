# 模块 24: 安全最佳实践

English: [24-security-best-practices.md](24-security-best-practices.md) | 上一课: [23-logging-monitoring-and-auditing](23-logging-monitoring-and-auditing.zh.md) | [课程主页](../README.zh.md) | 下一课: [25-common-errors-and-troubleshooting](25-common-errors-and-troubleshooting.zh.md)

## 5W + How

- **What（是什么）:** 最小权限、短寿命令牌、PKCE、精确回调 URI、audience 校验、无密钥工作负载、失败关闭默认。
- **Why（为什么）:** 错误的身份边界会导致混淆代理与静默越权。
- **Who（谁）:** 所有构建者与评审者。
- **When（何时）:** 作为任何身份变更的发布检查清单。
- **Where（何处）:** 身份与策略位于客户端、IdP、API 与工具之间的信任边界。
- **How（怎么做）:** 先掌握词汇与时序，实现最小校验，不匹配则失败关闭。

## 图示

```mermaid
flowchart TB
    L[Least privilege scopes] --> S[Short TTL + rotation]
    S --> V[Validate iss/aud/exp/sig]
    V --> F[Fail closed]
```

## 代码

```python
checklist = ["pkce", "exact_redirect", "aud_check", "no_id_token_as_bearer", "rotate_refresh"]
assert "aud_check" in checklist
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

- Wiki: [安全最佳实践](https://github.com/xingaiapp/xingai-ai-learning-wiki/blob/main/wiki/concepts/oauth-oidc-azure-identity/24-security-best-practices.zh.md)
- 实验: [OAuth 2.1 + PKCE MCP](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-pkce-lab.md)
- 深读: [MCP OAuth 认证](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-auth-deep-dive.md)
- 规范: [OAuth 2.1](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-v2-1-13) · [OIDC Core](https://openid.net/specs/openid-connect-core-1_0.html) · [Entra ID 文档](https://learn.microsoft.com/entra/identity/)
