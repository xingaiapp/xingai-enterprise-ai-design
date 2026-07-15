---
title: Anthropic 的 Loop Engineering 入门——面向 Agent 工作的四种循环
author: Xing Wang
date: 2026-07-15
tags: [architecture, enterprise, loop-engineering, agents, claude-code, mcp, education, design-patterns]
description: Anthropic 于 2026-06-30 发布了 Claude Code 的 Loop Engineering 官方指南。本文梳理其对 Loop 的定义、四种循环类型、验证与 Token 成本原则，以及它在 XingAI「Prompt → MCP → Loop」Agent 教程时间线里的位置。
---

# Anthropic 的 Loop Engineering 入门：面向 Agent 工作的四种循环

**2026 年 6 月 30 日**，Claude Code 团队发布了 [Loop engineering: Getting started with loops](https://claude.com/blog/getting-started-with-loops)。这是目前厂商侧对 **Loop Engineering（循环工程）** 最清楚的官方定义之一：不是新论文，而是一支天天跑 Agent 的团队给出的实用分类。

XingAI 此前已在 [Beyond Prompt Engineering](2026-07-03-beyond-prompt-engineering-loop-engineering.zh.md) 与 [从 Prompt 到 Loop](2026-07-03-prompt-to-loop-ai-native-architecture.zh.md) 里把企业 AI 写成「运行时 / 循环」问题。本文是配套阅读笔记：Anthropic 说了什么、对 Agent / MCP 教程意味着什么、以及它在工程知识时间线里该放在哪。

> 原始来源：Delba de Oliveira & Michael Segner，*[Loop engineering: Getting started with loops](https://claude.com/blog/getting-started-with-loops)*，Claude / Anthropic，2026-06-30。下文解读为 XingAI 观点。

---

## 为什么这篇文章重要？

过去几年常见的公开阶梯是：

```text
Prompt Engineering
        │
        ▼
Context Engineering
        │
        ▼
Agent Engineering
```

Claude Code 把设计对象推成：

```text
Loop Engineering
```

他们的核心判断很直接：**真正需要设计的，首先不是 Prompt，而是 Agent 持续工作的 Loop——直到停止条件被满足。**

这与 XingAI 在平台侧谈的 Loop Engineering 同向。Anthropic 这篇给出编码 Agent 原生的词汇：触发方式、停止条件、验证 Skills，以及何时不必上重 Loop。

---

## Anthropic 对 Loop 的定义

官方定义（按原文意译）：

> **Loop = Agent 重复执行工作，直到满足停止条件（Stop Condition）。**

实践上可画成：

```text
Goal
   │
   ▼
Plan
   │
   ▼
Execute
   │
   ▼
Verify
   │
   ▼
Need more work?
   │
  Yes ──────────────┐
   │                │
   ▼                │
 Iterate ───────────┘
   │
  Done
```

这很眼熟：它是 **ReAct**（推理 → 行动 → 观察 → 再来）的生产形态亲缘，但把 **停止条件** 写死了，并更强调 **外部可验证** 的完成标准。

---

## 四种 Loop

Anthropic 按触发、停止与任务形态分类：

| 类型 | Trigger | Stop | 适合 |
| --- | --- | --- | --- |
| **Turn-based** | 用户 Prompt | Agent 自判结束（或需要更多上下文） | 短任务、一次性问答 |
| **Goal-based** | 用户定义的 Goal（`/goal`） | 达到 Goal **或** 达到次数上限 | 可验证工作（测试、分数、CI） |
| **Time-based** | 定时（`/loop`、`/schedule`） | 你取消，或外部工作完成 | 循环运维：盯 PR、早间摘要 |
| **Proactive** | 事件 / 日程，实时无人值守 | 单次任务靠 Goal 退出；例程一直跑到关掉 | 持续涌入的确定性工作流（Bug、分拣、升级） |

### ① Turn-based Loop

经典聊天 + 工具路径：

```text
User → LLM → Tool → LLM → Return
```

外层循环仍由你关掉。你脑子里的「它到底有没有真的好」——在编码成 **Skill** 之前——仍然只在你脑子里。有了验证 Skill，Agent 才能在交回结果前多做一段自检。

### ② Goal-based Loop（`/goal`）

Anthropic 的例子：

```text
/goal get the homepage Lighthouse score to 90 or above, stop after 5 tries.
```

Agent：跑 → 量 → 不够 → 再跑，直到过线或耗尽尝试次数。

关键设计原则：**「完成」由明确标准来判（理想情况下由评估器判），而不是同一个模型随口说「看起来可以了」。** 确定性检查——测试通过、分数门槛、CI 绿——比 vibe 靠谱。

这也是当前 Agent Engineering 的最佳实践。`/goal` 只是把停止条件升成了一等原语。

### ③ Time-based Loop（`/loop` / `/schedule`）

例如：

```text
/loop 5m check my PR, address review comments, and fix failing CI
```

或每天早上总结 Slack → 发日报。工作形状不变，输入每次不同。本机 `/loop` 关机即停；云端 `/schedule` 把节拍从笔记本上挪走。

### ④ Proactive Loop

把日程 + Goal + 验证 +（可选）多 Agent Review 组成例程，不需要人为每个工单点一次。官方 Bug 反馈例子：每小时扫报告，分拣 / 修复 / Review / 回复，必要时开 auto mode，以免每一步都停下来要权限。

人们说的 **真正 Autonomous Agent**，大致就是这个形状——而治理、审计与成本控制在这里不再是可选项。

---

## Claude 给出的 Loop 设计原则

Loop 输出质量取决于它周围的系统：

1. **Codebase 保持整洁** —— Agent 会抄仓库里已有的习惯。
2. **验证 Skills** —— 把「什么算好」写成可度量检查，而不是表演式收尾。
3. **新鲜上下文的 Reviewer** —— 第二个没写过改动的 Agent（或 `/code-review`）。
4. **修系统，而不只修这一次** —— 某次不达标时，把教训写回文档 / Skill / 检查，让下一轮变好。

XingAI 侧对应的栈可以写成：

```text
Prompt / 意图
        │
        ▼
Loop（触发 + 停止）
        │
        ▼
Verification（Skills、测试、账本）
        │
        ▼
Tools / MCP
        │
        ▼
Reviewer / 人工闸门（高风险时）
        │
        ▼
继续或退出
```

---

## Token 控制建议

Anthropic 的成本建议不花哨，但演示里经常被无视：

- 不是所有任务都要上复杂 Loop —— 先选能用的最简单类型。
- 写清 **Goal 与硬停止条件**，避免无限转。
- **大规模跑之前先小规模试**。
- 确定性工作优先用 **脚本**；不要每次让模型重新推一遍填表逻辑。
- 定时频率不要超过被监视对象的真实变化速度。
- 用用量工具（`/usage`、`/goal` 状态、workflow token）杀掉失控 Agent。

对 XingAI 产品：先定清楚功能是 **哪一种 Loop**，再接线 MCP。定时刷新决策缓存的 worker 是带预算的 *time-based*；分析页一次点击是 *turn-based*。不写清停止条件就把两者搅在一起，账单和静默错答都会来。

---

## 对 AI Agent / MCP 教程的价值

建议参考文献按时间线组织：

| 年份 | 文献 | 贡献 |
| --- | --- | --- |
| 2022 | [ReAct](https://arxiv.org/abs/2210.03629) | 推理 + 行动循环 |
| 2023–2025 | OpenAI Function Calling / Anthropic Tool Use | 工具调用机制 |
| 2025–2026 | [MCP Specification](https://modelcontextprotocol.io/specification) | 标准化工具协议 |
| 2026 | [Building Effective AI Agents](https://www.anthropic.com/engineering/building-effective-agents) | Workflow vs Agent |
| **2026-06-30** | **[Getting started with loops](https://claude.com/blog/getting-started-with-loops)** | **厂商侧 Loop 分类（Claude Code）** |
| 2026-07 | XingAI Loop Engineering 系列 | 企业运行时 / 平台视角 |

教程可教的演进脉络：

```text
Prompt Engineering
        │
        ▼
Function Calling / Tool Use
        │
        ▼
ReAct
        │
        ▼
Agent（turn-based）
        │
        ▼
MCP（工具边界）
        │
        ▼
Loop Engineering（goal / time / proactive）
        │
        ▼
Autonomous Agent OS（带闸门、审计、成本）
```

把 **Anthropic 的四种类型** 放进 **Agent Loop** 那一章。旁边放 XingAI 更早的两篇，讲企业运行时、决策账本、Invest 决策缓存边界——Claude 这篇偏编码 Agent 原生；XingAI 偏产品与平台原生。

链接也收在 [`docs/xingai-engineer-learning-resources.md`](../docs/xingai-engineer-learning-resources.md)。

---

## 收束

Anthropic 并不是在 2026 年 6 月发明了「会循环的 Agent」。他们发布的是一套 **可分享的分类法**：停止条件、验证与成本规则，能直接教，不必玄学。

若只记一句： **先设计 Loop 与停止条件；Prompt 只是某一回合怎么开场。**

---

## 参考文献

- Delba de Oliveira & Michael Segner，[Loop engineering: Getting started with loops](https://claude.com/blog/getting-started-with-loops)，Anthropic / Claude，2026-06-30
- Yao et al.，[ReAct: Synergizing Reasoning and Acting in Language Models](https://arxiv.org/abs/2210.03629)，2022
- Anthropic，[Building Effective AI Agents](https://www.anthropic.com/engineering/building-effective-agents)
- Model Context Protocol，[Specification](https://modelcontextprotocol.io/specification)
- Xing Wang，[Beyond Prompt Engineering](2026-07-03-beyond-prompt-engineering-loop-engineering.zh.md)
- Xing Wang，[从 Prompt 到 Loop](2026-07-03-prompt-to-loop-ai-native-architecture.zh.md)

## 免责声明

面向 XingAI 工程师与教程作者的教育性整理。不构成法律、合规或 Anthropic 产品建议。CLI 与产品能力以 [Anthropic 原文](https://claude.com/blog/getting-started-with-loops) 为准；`/goal`、`/loop`、`/schedule` 等原语可能变更。
