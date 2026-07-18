---
title: "LLM 应用护栏：Plan → Build → Validate → Operate 不是工具目录"
author: Xing Wang
date: 2026-07-17
tags: [architecture, enterprise, guardrails, monitoring, mcp, rag, governance, education, design-patterns]
description: 十二步 LLM 护栏阶梯需要墙、证据停止条件与 Decision Ledger——而不是每个盒子下面的 Tools 行。
---

# LLM 应用护栏：Plan → Build → Validate → Operate 不是工具目录

面向企业架构师与平台负责人：你们大概见过同一张病毒图——十二步、四个阶段、每张卡下面一排 **Tools**。

那张图有用。它不是控制平面。

## 问题

团队把海报当成购物清单。

- “加了 LangChain”＝“有了 RAG”
- “加了 LangSmith”＝“有了监控”
- “加了 Docker”＝“安全部署完了”

与此同时，生产 Agent 仍信任检索文本、只用 scope 放行工具、只量延迟。出事时，没有人能指出一次 Agent Run 或一行 ledger。

## 模式

保留四个阶段。改写每个阶段的含义。

```text
Plan
  1 用例 + 失败代价
  2 风险 / 策略矩阵  ← 在选模型之前

Build
  3 按任务选模型（不是版本贴纸）
  4 证据 RAG + 充分性停止
  5 Prompt + 输出契约 + 拒绝规则
  6 净化所有不可信观测
  7 MCP 双墙工具 + 副作用前持久审批

Validate
  8 输出闸门（拒绝 / 修复 / 升级）
  9 Agent Run 追踪（目标 → 工具 → 结果）
 10 评测 / 红队 + 发布阻断

Operate
 11 身份 / 网关 / 密钥作为持续控制
 12 迭代 + Decision Ledger（事故 → 新测试）
```

**不变量：** Agent 推理可以是概率性的。认证、工具授权与工作流状态必须保持确定性与可恢复。

## Tools 行错在哪里

Tools 行回答“哪个产品可能有用”。架构回答：

- 什么不可信？
- 副作用前哪道墙会触发？
- 证据到什么程度该回答 vs 升级人工？
- 什么记录证明我们放行或拒绝？

若图离开厂商名就答不上来，它仍是目录。

## XingAI 参考

可运行演示（mock 模型、失败关闭、四个探针）：

- POC：[llm-guardrails-monitoring-poc](https://github.com/xingaiapp/xingai-enterprise-ai-pocs/tree/main/pocs/llm-guardrails-monitoring-poc)
- ADR-010：[docs/adr/010-llm-guardrails-monitoring-poc.zh.md](https://github.com/xingaiapp/xingai-enterprise-ai-pocs/blob/main/docs/adr/010-llm-guardrails-monitoring-poc.zh.md)
- 工程博文：[十二步不是十二个工具 Logo](https://github.com/xingaiapp/xingai-tech-blog/blob/main/posts/2026-07-17-llm-guardrails-twelve-steps-not-tool-stickers.zh.md)

真实 OAuth + 策略墙机制见 [claims-mcp-oauth-poc](https://github.com/xingaiapp/xingai-enterprise-ai-pocs/tree/main/pocs/claims-mcp-oauth-poc)——本护栏 POC 不替代它。

## 相关设计文档

- EN: [Beyond Prompt Engineering: Loop Engineering](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-07-03-beyond-prompt-engineering-loop-engineering.md)
- 中文: [超越提示工程：循环工程](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-07-03-beyond-prompt-engineering-loop-engineering.zh.md)
- EN: [Agent Governance Reference Architecture](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-07-05-agent-governance-reference-architecture.md)
- 中文: [Agent 治理参考架构](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-07-05-agent-governance-reference-architecture.zh.md)
- EN: [Third-Party MCP Auth: API Key vs OAuth2](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-07-15-third-party-mcp-auth-api-key-vs-oauth2.md)
- 中文: [第三方 MCP 认证：API Key vs OAuth2](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-07-15-third-party-mcp-auth-api-key-vs-oauth2.zh.md)

## 免责声明

教育 / 信息用途。不是法律、合规、安全认证或专业意见。读者自行承担部署风险。
