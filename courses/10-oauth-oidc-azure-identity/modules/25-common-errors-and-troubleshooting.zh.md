# 模块 25: 常见错误与排障

English: [25-common-errors-and-troubleshooting.md](25-common-errors-and-troubleshooting.md) | 上一课: [24-security-best-practices](24-security-best-practices.zh.md) | [课程主页](../README.zh.md) | 下一课: [26-complete-azure-reference-architecture](26-complete-azure-reference-architecture.zh.md)

## 5W + How

- **What（是什么）:** 多数认证故障来自回调不匹配、错误 audience、令牌过期、时钟偏差、缺少 PKCE，或混淆 ID/Access Token。
- **Why（为什么）:** 错误的身份边界会导致混淆代理与静默越权。
- **Who（谁）:** 值班工程师、集成方。
- **When（何时）:** 出现登录或 API 401/403 时——先调试声明再重写应用。
- **Where（何处）:** 身份与策略位于客户端、IdP、API 与工具之间的信任边界。
- **How（怎么做）:** 先掌握词汇与时序，实现最小校验，不匹配则失败关闭。

## 图示

```mermaid
flowchart TB
    E401[401/403] --> Q1{Token present?}
    Q1 -->|no| Login[Fix login / acquire]
    Q1 -->|yes| Q2{iss/aud/exp ok?}
    Q2 -->|no| Claims[Fix validation]
    Q2 -->|yes| Q3{scope/policy?}
    Q3 -->|no| AuthZ[Fix authorization]
```

## 代码

```python
def classify(status: int, aud_ok: bool) -> str:
    if status == 401 and not aud_ok:
        return "audience_or_issuer"
    if status == 403:
        return "authorization"
    return "other"
assert classify(401, False) == "audience_or_issuer" 
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

- Wiki: [常见错误与排障](https://github.com/xingaiapp/xingai-ai-learning-wiki/blob/main/wiki/concepts/oauth-oidc-azure-identity/25-common-errors-troubleshooting.zh.md)
- 实验: [OAuth 2.1 + PKCE MCP](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-pkce-lab.md)
- 深读: [MCP OAuth 认证](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-auth-deep-dive.md)
- 规范: [OAuth 2.1](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-v2-1-13) · [OIDC Core](https://openid.net/specs/openid-connect-core-1_0.html) · [Entra ID 文档](https://learn.microsoft.com/entra/identity/)
