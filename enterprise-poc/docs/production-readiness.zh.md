# 生产就绪检查清单

English: [production-readiness.md](production-readiness.md)

任何清单都不能自动授予生产批准；具名 Owner 必须附上证据并接受剩余风险。

- 身份：验证 Issuer/Audience/Signature/Key Rotation/Workload Identity。
- 授权：Tenant 隔离、RBAC/ABAC/Scope、Step-up、拒绝原因、负向测试。
- 数据：分类、Consent、Provenance、Retention、删除、Backup、Restore、加密。
- RAG：排序前 ACL、检索/依据性评估、投毒防御、Stale 语义。
- Agent：限制工具/步骤/时间/成本，类型化 Handoff，无进度停止，人工升级。
- MCP：Protected Resource Metadata、Resource Indicator、Audience Binding、最小权限、审批。
- 安全：Threat Model、红队、Dependency/SBOM、Secret、Egress、SSRF、事故流程。
- 可靠性：SLO/Error Budget、Capacity、Backpressure、幂等、Canary、Rollback、RTO/RPO。
- 可观测性：脱敏 Logs、Metrics、Traces、Correlation、有 Owner Alert、结果监控。
- 审计：不可变存储、事件 Schema、排序、访问、保留、校验、导出。
- 评估：版本化代表/对抗数据、人工校准、发布 Gate、Drift。
- 组织：具名领域 Owner、SRE/客服、法务/隐私/风险批准、培训与终止标准。

