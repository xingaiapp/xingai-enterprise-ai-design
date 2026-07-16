# 运营 Runbook

English: [runbooks.md](runbooks.md)

每次事故都应：声明 Severity 与 Incident Commander、停止不安全写入、保留证据、识别受影响 Tenant、沟通、缓解、验证恢复，并安排无责纠正评审。

| 触发条件 | 立即控制 | 恢复证据 |
|---|---|---|
| 不安全操作 | 禁用写工具；保留 Trace/Audit | 授权与审批测试通过 |
| 跨 Tenant 结果 | 停止检索；撤销受影响索引/版本 | 零泄露回归 Suite 通过 |
| 模型退化 | 路由至批准 Fallback 或人工评审 | Eval Gate 与 Canary 通过 |
| 授权故障 | 受保护操作 Fail Closed | 策略服务与负向测试健康 |
| 审计写入失败 | 阻止高影响写入 | Durable Audit 连续性验证 |
| 队列积压 | 应用 Backpressure；暂停 Proactive Loop | Queue Age 与 SLO 恢复 |
| 成本激增 | 降低预算；禁用非必要 Agent | 单位成本回到预算内 |

