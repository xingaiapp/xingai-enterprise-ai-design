# Claims Copilot Agent — 工程实战课

领域课：设计、开发、加固、评估并讲清企业级 **Claims Copilot Agent（理赔智能助理）**。业务词汇配合 [理赔业务课](../claim-business/README.zh.md)；Agent / MCP / 生产基础配合系列课 [03](../03-tool-use-ai-agents/README.zh.md)–[06](../06-production-ai-engineering/README.zh.md)。

## 文档

| 语言 | 文件 |
|------|------|
| 简体中文 | [claims-copilot-agent-guide-zh.md](./claims-copilot-agent-guide-zh.md) |
| English | [claims-copilot-agent-guide-en.md](./claims-copilot-agent-guide-en.md) |

双语为完整对等版本。中文保留关键英文标识符（如 `Agent`、`MCP`、`OBO`、`Golden Dataset`）。

## 贯穿项目

> **Claims Copilot Agent**：摘要 Claim、识别风险、查询 Policy、建议下一步，并在人工批准后添加 Claim Note。

示意理赔运营场景，**不是**客户保密 SOP 或生产库表结构。

## 受众

- 会调 LLM API，但需要企业级 Agent 能力用于交付与面试的工程师
- 进入理赔 / 保险科技项目的架构师（优先 Azure、.NET、Entra ID；本地实验可用 SQLite）

## 学习方法

1. 不熟 Tool Calling 时，先完成系列课 03，再进入第 3 章。
2. 快速过一遍理赔业务课 Level 1–2（Adjuster / Claim 词汇）。
3. 动手写工具前先完成第 1–2 章。
4. 按 Newbie → Expert 路线在私有作品集仓库里增量实现。
5. 通过验收清单（10 道答辩题）后，再把项目写进简历。

## 相关

- 课程契约：[../COURSE-STANDARD.zh.md](../COURSE-STANDARD.zh.md)
- 身份专题：[../10-oauth-oidc-azure-identity/README.zh.md](../10-oauth-oidc-azure-identity/README.zh.md)
- 教学 POC：`xingai-enterprise-ai-pocs`（非生产理赔平台）
