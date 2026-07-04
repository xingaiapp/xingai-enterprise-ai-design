---
title: "超越 Prompt Engineering：为什么企业 AI 是一个运行时问题"
author: Xing Wang
date: 2026-07-03
tags: [architecture, enterprise, loop-engineering, context-engineering, harness-engineering, agent-runtime, governance, ai-platform]
description: 下一个竞争优势不是更好的模型——而是 Loop Engineering。本文梳理从 Prompt 到 Platform 的演进路线，解释为什么企业 AI 的持久资产是运行时，而非模型本身。
---

# 超越 Prompt Engineering：为什么企业 AI 是一个运行时问题

### 下一个竞争优势不是更好的模型——而是 Loop Engineering

> *"企业 AI 最大的变化不是更好的模型，而是一种全新的软件架构。"*

如果你关注过去一年 AI 行业的发展，会发现这个学科大约每个季度就自我重塑一次。我们从 Prompt Engineering 起步，然后意识到没有正确的信息，prompt 毫无用处，Context Engineering 取而代之。接着我们给模型配备了工具和运行时，Agent Engineering 随之出现。现在前沿再次推进——到了我称为 **Loop Engineering** 的阶段：设计能够自主追求目标、一轮接一轮迭代的系统，不需要人类驱动每一步。

残酷的现实是：很多组织还在 A/B 测试 prompt 措辞，而领先的 AI 团队已经围绕自主系统重新设计整个软件架构。这篇文章会展示我认为的新架构全貌——以及为什么企业的持久资产不是你的 prompt、甚至不是你选的模型，而是你的运行时。

## 演进：从 Prompt 到 Platform

演进路径如下：

```
Prompt Engineering
        │
        ▼
Context Engineering
        │
        ▼
Harness Engineering
        │
        ▼
Loop Engineering
        │
        ▼
AI-Native Platform
```

每个阶段不只是增加技术手段——它改变了工程师所*负责的事*：

| 阶段 | 聚焦 | 目标 |
| --- | --- | --- |
| Prompt Engineering | 更好的提示词 | 更好的回答 |
| Context Engineering | 更好的信息 | 更好的推理 |
| Harness Engineering | 更好的执行 | 更好的任务完成 |
| Loop Engineering | 更好的自主性 | 更好的结果 |

关键转折在最后一步。Loop Engineering 之前的所有阶段都是让 AI *更好地回答问题*。Loop Engineering 是构建*持续达成目标*的系统。这是根本不同的工程问题。

## Prompt 驱动 vs. Loop 驱动

传统 AI 应用是 prompt 驱动的。人类提出请求，模型响应，只有人推动才能继续循环：

```
Human → Prompt → LLM → Response
```

每一次交互都需要一个人参与——你的 AI 系统吞吐量被人类的注意力锁死。

企业 AI 正转向 loop 驱动模型，工作单元不再是一条消息，而是一个*目标*：

```
Goal → Plan → Execute → Evaluate → Reflect → Continue?
                                                ├── Yes ──┐
                                                │         │
                                                └── No    └──▶ back to Plan
```

人类设定目标和约束条件；系统编排执行步骤。设计问题从 *"我应该怎么写 prompt？"* 变成了 *"系统应该持续优化什么结果？在什么防护栏下？"*

## 现代 AI 系统的三层架构

一个生产级 AI Agent 不再是带漂亮 UI 的 prompt。它是三个不同工程层的堆叠，各自有不同的关注点：

```
+--------------------------------------+
| Loop Engineering                     |
| 调度 • 反思 • 自主性                   |
+--------------------------------------+
| Harness Engineering                  |
| Agent • 工具 • 技能 • 运行时           |
+--------------------------------------+
| Context Engineering                  |
| Prompt • 记忆 • RAG • 知识            |
+--------------------------------------+
```

### 第一层：Context Engineering —— 模型知道什么

Context Engineering 回答一个问题：**模型在开始思考之前知道什么？** 这包括系统指令、用户画像、长期记忆、对话历史、检索的知识 (RAG)、工具结果和运行时状态。

这一层至关重要，因为再强的模型能力也弥补不了信息缺失。一个没有上下文的强模型依然是盲的——只是幻觉得更自信。

### 第二层：Harness Engineering —— 工作怎么完成

如果 Context 是大脑的知识，Harness 就是操作系统。它管理工具调用、技能、记忆持久化、多 Agent 协作、状态、结构化输出、权限和运行时隔离。

关键的架构转变是：LLM 不再是直接解决一切的组件。它成为执行环境中的推理核心：

```
LLM → Planner → Tools → { Browser, GitHub, Database } → Memory → Evaluation
```

模型决定*做什么*；Harness 管控*怎么做*——安全、可观测、有正确的权限。

### 第三层：Loop Engineering —— 工作何时发生、何时停止

这一层让 AI 真正变得自主，核心是三个看似简单的问题：

1. **执行从哪里开始？**（入口点）
2. **什么在重复？**（循环体）
3. **什么时候停？**（终止条件）

每个生产级循环必须定义全部三项。跳过任何一个，你的自主 Agent 就退化为一个有企业信用卡的无限 token 生成器。

**入口点**可以是用户请求、cron 定时任务、webhook、GitHub 事件或 Slack 消息。触发器决定了谁——或什么——有权消耗你的算力。

**循环体**通常是 plan → execute → evaluate → reflect 周期。evaluation 和 reflection 步骤将循环与重试区分开来：系统不只是再试一次，而是*不同地*再试，基于上一轮的结果。

**终止条件**是整个架构中最被忽视的部分。生产系统在以下条件下停止：目标达成、最大迭代次数到达、时间限制超时、预算耗尽、质量阈值满足，或者——至关重要的——*没有检测到进展*。没有明确的终止条件，系统永远不会停止思考，而"永不停止思考"在按 token 付费时并不是一个功能。

## 防护栏不是可选项

没有防护栏的自主性是负债，不是能力。每个企业循环至少应该配备：

- **最大迭代次数** —— 例如每个任务硬上限 5 轮循环。
- **Token 预算** —— 例如每次运行 100K token，由 Harness 强制执行，而非模型自身。
- **进度检测** —— 如果连续两轮迭代没有可衡量的改进，自动停止。停滞的循环浪费金钱、掩盖 bug。
- **超时** —— 墙钟时间限制，防止 Agent 无限运行，不管它们认为自己在做什么。
- **人工审批关卡** —— 高风险操作升级到人。部署生产代码、发送客户邮件、做金融决策，都不应在无人监督的循环中完成。

注意这些全都在 Harness 和 Loop 层中，不在 prompt 里。你不可能通过 prompt 获得安全保证。

## 企业 Agent 的 15 个构建模块

盘点生产 Agent 实际需要什么，模型只是物料清单中占比很小的部分。我在三个组中数出十五个构建模块：

**基础与知识** —— 规范引擎、知识中心、技能库、上下文引擎和记忆。

**执行与连接** —— 工具、多 Agent 协作、异步通信和结构化输出。

**治理** —— 权限、工作流编排、并行执行、状态管理、AI 评估和可观测性。

这些都不是锦上添花。在企业环境中，它们是刚需——就像日志、认证和 CI 对传统服务从来不是可选项一样。

## 从硬编码 Agent 到 Micro Loop Engine

今天，大多数团队手工构建每个 Agent：一个 Agent、一套配置、一次部署。这不具备扩展性，因为不同的业务问题需要不同的能力组合——研究 Agent 不应使用与编码 Agent 相同的配置。

我认为会胜出的模式是动态组装。**Micro Loop Engine** 接收业务请求，按需组合出定制的运行时：

```
Business Request
      │
      ▼
Micro Loop Engine
      │
      ├─ 选择 Skills
      ├─ 选择 Tools
      ├─ 选择 Memory
      ├─ 选择 Agents
      ├─ 配置 Loop
      │
      ▼
Deploy Runtime
```

这和企业软件已经完成过的一次转型如出一辙：从单体（"一个应用、一个流程、一次部署"）到可组合平台。在 AI 原生架构中，可复用的组件是运行时、技能、记忆、工具和循环——运行时本身成为多个应用共享的平台。

## 全景：AI 原生平台架构

把视野拉到最远，企业 AI 平台分解为两个互补的半边。

**功能架构**负责完成工作：流量层、API 网关、消息队列、Planner Agent、业务 Agent、技能、AI 网关、模型层、MCP/工具、知识和记忆。

**治理架构**保证可信：配置中心、Agent 注册中心、评估中心、AI 安全、AI 治理和弹性扩缩容。

数一下层次，注意一件事：**模型只是其中之一。** 其余的十六层——才是企业价值真正被创造的地方。这应该重新定义你的工程投资方向。

## 模型可替换，运行时不可替换

很多公司仍然相信自己的 AI 护城河是更好的 prompt 或使用更好的模型。我不同意，理由很简单：每家公司都能购买 GPT、Claude、Gemini 或 DeepSeek。模型访问是有价目表的商品。

很少有公司拥有：

- **决策记忆** —— 组织做了什么决定、为什么做的持久记录
- **工作流智能** —— 编码了工作实际如何完成的知识
- **评估系统** —— 衡量 AI 输出是否真正好的能力
- **Agent 运行时** —— 可复用的 Harness 基础设施：工具注册表、沙箱、状态管理器、权限系统
- **反馈循环** —— 决定何时运行、执行什么、何时重试、何时停止的调度器和评估器

最后一项——循环调度器和评估层——值得深思。它是模型*之上*的智能，不同于模型的是，它会增值：每次运行都让它更好地校准你的业务。模型在更好的模型发布那天就贬值。运行时会升值。

## 构建决策操作系统，而非又一个聊天机器人

如果你接受以上论点，战略结论自然浮现：企业 AI 团队不应该构建聊天机器人。他们应该构建**决策操作系统（Decision Operating System）**——一个让业务目标流经规划、研究、推理、执行、评估和反思的平台，每个周期的*学习*反馈到下一个决策：

```
Business Goal → Planner → Research → Reasoning → Execution
                                                     │
      Next Decision ◀── Learning ◀── Feedback ◀── Evaluation
```

由此产生的系统持续改进*决策*，而非对话。这就是 AI 功能和 AI 平台的区别。

对于正在朝这个方向设计的团队，我的架构优先级是：

- **目标优先于提示词** —— 为结果设计，而非为措辞设计
- **运行时优先于模型** —— 投资于价值复合增长的地方
- **记忆优先于对话** —— 持久化跨会话的重要信息
- **评估优先于生成** —— 衡量质量胜过产出数量
- **循环优先于工作流** —— 自适应迭代胜过僵化管道
- **可复用基础设施优先于一次性应用**
- **从第一天就开始治理** —— 事后补装防护栏的代价远高于提前设计

## XingAI 如何验证这些模式

XingAI 构建专注的 AI 决策系统——Invest AI、Meal Coach、Research AI、Polymarket AI 等。每个产品锻炼架构的不同切面：

| 产品 | 验证的层次 |
|------|----------|
| [Invest AI](https://github.com/xingaiapp/xingai-invest-ai) | Worker-cache CQRS、宏观 regime overlay、决策账本、人工审批执行关卡 ([ADR-028](https://github.com/xingaiapp/xingai-invest-ai/blob/main/docs/adr/028-robinhood-mcp-execution-gates.md))、个人记忆引擎 ([ADR-031](https://github.com/xingaiapp/xingai-invest-ai/blob/main/docs/adr/031-personal-memory-engine-api.md)) |
| [Decision Engine](https://github.com/xingaiapp/xingai-invest-decision-engine) | 多时间框架评分循环、只读 broker harness ([ADR-014](https://github.com/xingaiapp/xingai-invest-decision-engine/blob/main/docs/adr/014-robinhood-mcp-readonly.md))、跨产品决策账本 ([ADR-016](https://github.com/xingaiapp/xingai-invest-decision-engine/blob/main/docs/adr/016-cross-product-decision-ledger.md)) |
| [Enterprise POCs](https://github.com/xingaiapp/xingai-enterprise-ai-pocs) | Supervisor 编排 ([ADR-001](https://github.com/xingaiapp/xingai-enterprise-ai-pocs/blob/main/docs/adr/001-supervisor-audit-human-in-the-loop.md))、MCP 网关治理 ([ADR-003](https://github.com/xingaiapp/xingai-enterprise-ai-pocs/blob/main/docs/adr/003-mcp-gateway-placeholder-policy.md))、事件总线设计 ([ADR-004](https://github.com/xingaiapp/xingai-enterprise-ai-pocs/blob/main/docs/adr/004-event-bus-ai-review-placeholder.md)) |
| [Polymarket AI](https://github.com/xingaiapp/xingai-polymarket-ai) | Scanner-to-confirm 循环、Kelly sizing harness、Telegram 通知 vs 确认边界 ([ADR-004](https://github.com/xingaiapp/xingai-polymarket-ai/blob/main/docs/adr/004-telegram-notify-vs-confirm.md)) |

模式是一致的：**模型生成智能；运行时交付价值；循环创造自主性。**

## 结语

AI 行业正在经历十年前云计算走过的同一次转型。容器很有趣，但容器本身没有改变企业。改变一切的是组织围绕容器构建的生态：Kubernetes、服务网格、CI/CD、可观测性、基础设施自动化。容器是商品；平台才是价值。

企业 AI 正走在同一条路上。下一代 AI 平台不会由谁有最大的模型来定义。它们将由 **Context Engineering** 的质量、**Harness 基础设施**的健壮性和 **Loop Engineering** 的自主性来定义。

**模型生成智能。运行时交付价值。循环创造自主性。**

这就是下一代企业 AI 架构的根基。

---

## 相关阅读

- [从 AI 演示到企业 AI 决策系统](./2026-06-07-enterprise-ai-decision-systems.zh.md) —— 本框架之前的成熟度模型
- [编排器 vs MCP 网关](./2026-06-13-orchestrator-vs-mcp-gateway.zh.md) —— 区分 Agent 编排与工具路由
- [XingAI 企业 Agent 平台](https://github.com/xingaiapp/xingai-enterprise-ai-pocs/blob/main/docs/ENTERPRISE-AGENT-PLATFORM.zh.md) —— 参考架构
- [XingAI 不是聊天机器人——它是决策引擎](https://github.com/xingaiapp/xingai-tech-blog/blob/main/posts/2026-07-01-xingai-decision-engine-not-chatbot.zh.md) —— 产品定位
