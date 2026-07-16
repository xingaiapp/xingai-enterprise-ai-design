# 模块 19: API Key 与 PAT

English: [19-api-keys-and-pats.md](19-api-keys-and-pats.md) | 上一课: [18-session-and-cookie-security](18-session-and-cookie-security.zh.md) | [课程主页](../README.zh.md) | 下一课: [20-oauth-oidc-vs-saml](20-oauth-oidc-vs-saml.zh.md)

## 5W + How

- **What（是什么）:** API Key 与个人访问令牌是共享密钥。它们能认证调用方，但通常缺少用户同意体验与细粒度 OAuth scope。
- **Why（为什么）:** 错误的身份边界会导致混淆代理与静默越权。
- **Who（谁）:** 内部自动化、有合同约束的合作伙伴集成。
- **When（何时）:** 第三方与用户委派优先 OAuth；密钥仅在可轮换、受限保管与监控下使用。
- **Where（何处）:** 身份与策略位于客户端、IdP、API 与工具之间的信任边界。
- **How（怎么做）:** 先掌握词汇与时序，实现最小校验，不匹配则失败关闭。

## 图示

```mermaid
flowchart LR
    Key[API key / PAT] --> Secret[Shared secret risk]
    OAuth[OAuth + PKCE] --> Consent[Consent + scopes + revocation]
```

## 代码

```python
def prefer_oauth(third_party: bool, user_delegated: bool) -> str:
    return "oauth" if third_party or user_delegated else "key_with_controls"
assert prefer_oauth(True, False) == "oauth" 
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

- Wiki: [API Key 与 PAT](https://github.com/xingaiapp/xingai-ai-learning-wiki/blob/main/wiki/concepts/oauth-oidc-azure-identity/19-api-keys-and-pats.zh.md)
- 实验: [OAuth 2.1 + PKCE MCP](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-pkce-lab.md)
- 深读: [MCP OAuth 认证](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-auth-deep-dive.md)
- 规范: [OAuth 2.1](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-v2-1-13) · [OIDC Core](https://openid.net/specs/openid-connect-core-1_0.html) · [Entra ID 文档](https://learn.microsoft.com/entra/identity/)
