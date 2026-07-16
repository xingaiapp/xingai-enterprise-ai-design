# 模块 10: Scope、角色与业务授权

English: [10-scope-role-business-authorization.md](10-scope-role-business-authorization.md) | 上一课: [09-jwt-bearer-opaque-pop](09-jwt-bearer-opaque-pop.zh.md) | [课程主页](../README.zh.md) | 下一课: [11-oidc-discovery-and-jwks](11-oidc-discovery-and-jwks.zh.md)

## 5W + How

- **What（是什么）:** Scope 描述 OAuth 能力；角色描述岗位职能；业务策略决定该对象是否允许被操作。
- **Why（为什么）:** 错误的身份边界会导致混淆代理与静默越权。
- **Who（谁）:** 产品负责人、安全、MCP 工具作者。
- **When（何时）:** 始终把 OAuth scope 与领域策略分开（双墙模型）。
- **Where（何处）:** 身份与策略位于客户端、IdP、API 与工具之间的信任边界。
- **How（怎么做）:** 先掌握词汇与时序，实现最小校验，不匹配则失败关闭。

## 图示

```mermaid
flowchart TB
    Scope[OAuth scope wall] --> Policy[Business policy wall]
    Policy -->|allow| Exec[Execute]
    Policy -->|deny| Audit[Deny + audit]
```

## 代码

```python
def two_wall(scopes: set[str], role: str, object_owner: str, actor: str, action: str) -> bool:
    if action not in scopes:
        return False
    if role == "support" and object_owner != actor:
        return False
    return True
assert two_wall({"claim.read"}, "owner", "u1", "u1", "claim.read")
assert not two_wall({"claim.read"}, "support", "u1", "u2", "claim.read")
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

- Wiki: [Scope、角色与业务授权](https://github.com/xingaiapp/xingai-ai-learning-wiki/blob/main/wiki/concepts/oauth-oidc-azure-identity/10-scope-role-business-authorization.zh.md)
- 实验: [OAuth 2.1 + PKCE MCP](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-pkce-lab.md)
- 深读: [MCP OAuth 认证](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-auth-deep-dive.md)
- 规范: [OAuth 2.1](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-v2-1-13) · [OIDC Core](https://openid.net/specs/openid-connect-core-1_0.html) · [Entra ID 文档](https://learn.microsoft.com/entra/identity/)
