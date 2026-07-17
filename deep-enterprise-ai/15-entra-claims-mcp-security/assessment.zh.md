# 考核与面试答辩

English: [assessment.md](assessment.md) | 课程：[README.zh.md](README.zh.md)

## 递进式面试阶梯

| 级别 | 必须能够答辩 |
|---|---|
| 初学者 | 认证与授权；OAuth 与 OIDC；ID 与访问令牌；401 与 403 |
| 工程师 | 授权码 + PKCE；state/nonce；令牌校验；会话与刷新生命周期 |
| 高级工程师 | Entra 应用/服务主体模型；scope/role/对象策略；APIM 与服务器纵深防御 |
| Staff | MCP OAuth 发现；工具授权；OBO；app-only 身份；多租户同意 |
| 架构师 | Claims CRUD 风险控制、并发、审批、审计证据与故障恢复 |
| CTO | 自建/采购、监管暴露、运营成本、责任归属、剩余风险与上线门禁 |

```mermaid
flowchart LR
    B["协议准确性"] --> E["实现"] --> S["安全权衡"] --> A["架构"] --> C["业务决策"]
```

## 场景问题

1. 为什么 Entra 正确签名的令牌仍可能被 API 拒绝？
2. 为什么第三方客户端与 Claims MCP 必须使用独立应用注册？
3. 哪种凭据属于客户端会话，哪种属于资源服务器？
4. `state`、`nonce` 和 PKCE 分别防什么？
5. 服务器何时返回 `401`、`403` 和 `409`？
6. 为什么从工具列表隐藏 `claims.void` 仍不够？
7. 为什么 Claims MCP 必须兑换令牌而不能透传入站令牌？
8. 哪些场景不应使用 OBO，而应使用托管身份或客户端凭据？
9. 人工确认、独立审批、幂等与乐观并发有何不同？
10. 如何证明谁修改了理赔，同时不泄露理赔数据或令牌？
11. Entra、APIM、Claims API 或审计管道故障时系统如何运行？
12. 即使 POC 通过，哪些因素仍会让你推迟生产上线？

```python
def passed(score: int, critical_findings: int) -> bool:
    return score >= 80 and critical_findings == 0
```

## 评分

协议正确性 20、实现 20、安全推理 25、运维 15、管理层权衡 20。答案必须说明假设、被否决方案、证据与剩余风险；只背定义无法通过高级级别。

