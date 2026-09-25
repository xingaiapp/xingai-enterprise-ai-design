# Claims Copilot Agent — 架构笔记

完整长文（双语 + poster）：

- [中文文章](../../articles/2026-09-25-claims-copilot-agent-phased-roadmap.zh.md)
- [EN](../../articles/2026-09-25-claims-copilot-agent-phased-roadmap.md)
- 课程：[claims-copilot-agent](../../courses/claims-copilot-agent/README.zh.md)

![Claims Copilot phased roadmap](./claims-copilot-agent-phased-roadmap-system-design-ux.png)

## 阶段速查

| 阶段 | 交付 |
|---|---|
| MVP | 单 Agent + 模拟工具 + 结构化摘要 |
| POC | MCP 桩 + 写操作 HITL + Citation |
| 生产形态 | Entra ID + OBO + 审计 + CI Golden Eval |
| 更后 | 评测变绿后再 Multi-Agent Review |

**铁律：** 先工具与批准，再 Multi-Agent。
