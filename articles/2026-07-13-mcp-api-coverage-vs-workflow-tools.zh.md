---
title: MCP 全量 API 覆盖 vs 工作流工具：一个理赔第三方对接案例
author: Xing Wang
date: 2026-07-13
tags: [architecture, enterprise, mcp, api-design, tool-gateway, insurance, claims, design-patterns]
description: 把一个现有 REST API 包装成 MCP 工具时，是暴露每一个端点，还是挑几个高层工作流工具？本文用理赔域两个走了相反路线的姊妹 POC——一个窄但有真实 OAuth，一个广但还没认证层——来拆解这个取舍，并给出一套选择框架。
---

# MCP 全量 API 覆盖 vs 工作流工具：一个理赔第三方对接案例

任何一支把现有 REST API 包装成 MCP server 的团队，几乎立刻就会撞上同一个岔路口：是把 API 的每一个端点都暴露出来、一个操作对应一个工具，还是挑几个高层工作流工具，把多次 API 调用打包成一个面向 agent 的动作？演示很少展示这个决策是怎么做出来的——它们展示的是*已经决定好之后*的工具列表。

本文用 `xingai-enterprise-ai-pocs` 里两个刻意走了相反路线的姊妹 POC，把这个取舍讲透：[`claims-mcp-oauth-poc`](https://github.com/xingaiapp/xingai-enterprise-ai-pocs/tree/main/pocs/claims-mcp-oauth-poc)（4 个精选工具，真实 OAuth 2.1 + PKCE）和 [`claims-partner-api-mcp-poc`](https://github.com/xingaiapp/xingai-enterprise-ai-pocs/tree/main/pocs/claims-partner-api-mcp-poc)（18 个工具，全量 CRUD，还没有认证层）。两者都不是"正确答案"——它们回答的是不同的问题，一个真正的生产部署两个答案都需要。

---

## 5W 框架

### What（是什么）

把 REST API 变成 MCP 工具的两种设计：

| | 全量 API 覆盖 | 窄工作流工具 |
|---|---|---|
| 工具数量 | 每个端点一个工具（或接近） | 一小撮，每个打包多次 API 调用 |
| Agent 灵活性 | 高——agent 自己组合操作 | 低——agent 只能做工作流允许的事 |
| 评审面 | 大——每个端点都是审计者要推理的工具 | 小——一套固定、可审计的动作 |
| "做完"所需时间 | 快——从 OpenAPI 规范到工具 schema 是机械映射 | 慢——得有人设计每个工作流的形状 |
| 业务规则放在哪 | 分散在调用方碰巧调用的任何一个工具里，或者推给后端 | 集中在工作流工具本身里（比如一个 Review→Adjudicate 拆分） |

### Who（谁该读）

- **企业/AI 架构师**：决定如何通过 MCP 暴露一个内部或面向第三方的 API
- **平台工程师**：为一个业务域搭建第一个 MCP server，要选起始范围
- **安全评审人员**：需要推理一个被授予的 token 到底能做什么
- **产品经理**：为第三方集成的首个版本定范围

### When（什么时候要做这个决定）

这个决定必须在写第一个工具**之前**做，而不是事后才发现——本文对比的两个 POC 都从同一个 OpenAPI 形状的业务域（保险理赔）出发，恰好在这个岔路口分道扬镳，这正是为什么并排对比它们有用：同一个域、同一批底层操作、相反的选择。

### Where（适用场景）

任何 MCP server 挡在一个现有或新设计的 REST/GraphQL API 前面的场景都适用：理赔系统、CRM、工单系统、支付处理器、HR 系统——任何"直接把 API 包一层"是显而易见的第一直觉、而真正的问题是"包"到底要包多字面意思的业务域。

### Why（为什么重要）

因为这个选择的后果，之后想改代价很高。先做全量覆盖，之后可能得给 18 个工具而不是 4 个补上细粒度授权。先做窄工作流工具，合作方一旦需要一个你没预料到的操作就会撞墙——然后你要么被动地加工具（结果又慢慢漂回全量覆盖），要么直接回绝集成请求。

---

## 两个 POC，并排对比

[`claims-mcp-oauth-poc`](https://github.com/xingaiapp/xingai-enterprise-ai-pocs/tree/main/pocs/claims-mcp-oauth-poc) 存在的意义很具体：证明一套真实的 OAuth 2.1 + PKCE + JWT 认证协议，加上一个双墙授权模型（OAuth scope *加上*一个独立的理赔权限策略检查），能从券商域干净地推广到保险理赔域。为了让这个证明保持清晰易读，它的工具面刻意收窄——`get_claim`、`get_policy_coverage`、`review_claim_decision`、`submit_claim_decision`——四个工具，每一个都容易对照前面的认证机制去推理。评审这个 POC 的人不需要去猜，持有 `claims.adjudicate` scope 的 token 是不是还能碰到另外十五个工具。

[`claims-partner-api-mcp-poc`](https://github.com/xingaiapp/xingai-enterprise-ai-pocs/tree/main/pocs/claims-partner-api-mcp-poc) 存在的意义正相反：证明一个理赔业务*整个*面向合作方的 API 表面——理赔提交、状态流转、备注、文件证据、保单核验、理赔人管理、赔付结算，一份 OpenAPI 3.1 契约里定义的 7 个业务域共 18 个端点——可以逐一映射成 MCP 工具而不至于映射失去一致性或变得没法评审，并且最终的 server 真的能端到端跑起来（一个小的 Express mock 上游实现同一份契约，整套栈 `docker compose up` 就能跑）。为了让*这个*证明保持干净，它刻意还没有第三方认证层——一次性给 18 个工具加真实 OAuth，会让人很难分辨一个 bug 到底出在 API 映射上还是认证检查上。

换个说法：`claims-mcp-oauth-poc` 回答的是"认证协议有没有效、能不能推广"；`claims-partner-api-mcp-poc` 回答的是"整个 API 表面能不能被覆盖而不至于映射散架"。两个 POC 都刻意没有想同时回答这两个问题——具体推理见 [ADR-007](https://github.com/xingaiapp/xingai-enterprise-ai-pocs/blob/main/docs/adr/007-claims-partner-api-mcp-poc-full-coverage.zh.md)。

## 一个真实部署两者都需要

一个生产级的第三方理赔集成，不是"这两个 POC 挑一个直接上线"——而是 `claims-partner-api-mcp-poc` 的覆盖广度，加上 `claims-mcp-oauth-poc` 的认证服务器挡在前面，逐工具校验 OAuth scope（`claims.read`、`claims.write`、`claims.adjudicate`、`documents.read`、`documents.write`、`policies.read`、`claimants.read`、`claimants.write`、`payments.read`、`payments.write`——已经在 `claims-partner-api-mcp-poc` 的 OpenAPI 契约里声明好了，只是还没强制执行）。这两个 POC 单独拿出来都不能安全地交给真实第三方：窄的那个覆盖的 API 不够多，除了它本来要做的那一个工作流之外派不上别的用场；广的那个没有办法区分不同合作方的凭证。

这是这个取舍的实际解法，不是一个把两边都削弱的折中：**把覆盖面和认证做成两块可以分别评审的东西，再把它们合并起来。** 在一个 POC 里同时把两者都做出来，往往会让评审者没法干净地评估任何一个属性——这个工具缺失，到底是因为 API 映射没做完，还是 scope 故意把它排除了？把两者分开做，直到各自都独立正确，就能消除这种含糊。

## 一个粗略的选择指南

- **先做窄（工作流工具）的时机：** 调用方 agent 的使用场景已经明确且固定（比如就是理赔判定辅助这一个工作流）；操作足够高风险，每个工具都需要单独的安全评审；或者你在验证一个*协议*（比如认证），不想让工具数量成为干扰变量。
- **先做广（全量覆盖）的时机：** 你还不知道第三方 agent 到底会怎么用这个 API，不想猜错方向；API 本身已经规范良好（有 OpenAPI 契约，或者很容易写出来）；眼下的目标就是证明"把现有 API 包成 MCP"这套机制端到端能跑通。
- **一旦"先做广"的成果真实到可能被真实第三方碰到，就要规划把两者合并**——过了原型阶段，没有逐工具授权的全量覆盖不是一个功能，而是一个负债。

## 相关

- [ADR-007：理赔第三方 API MCP POC——全量 API 覆盖，认证推迟](https://github.com/xingaiapp/xingai-enterprise-ai-pocs/blob/main/docs/adr/007-claims-partner-api-mcp-poc-full-coverage.zh.md)
- [ADR-006：理赔 MCP OAuth POC——真实认证，非占位](https://github.com/xingaiapp/xingai-enterprise-ai-pocs/blob/main/docs/adr/006-claims-mcp-oauth-poc-real-auth.zh.md)
- [pocs/claims-partner-api-mcp-poc/](https://github.com/xingaiapp/xingai-enterprise-ai-pocs/tree/main/pocs/claims-partner-api-mcp-poc) —— 本文的直接实现
- [pocs/claims-mcp-oauth-poc/](https://github.com/xingaiapp/xingai-enterprise-ai-pocs/tree/main/pocs/claims-mcp-oauth-poc) —— 上面那个 POC 缺失的认证层
- [生产环境里 MCP 如何真正运转](2026-07-11-mcp-in-production-robinhood-case.zh.md) —— 工具面设计之外的生产环境 MCP 议题
- [从零搭建 OAuth 2.1 + PKCE MCP 项目](../guides/2026-07-12-mcp-oauth-pkce-lab.zh.md) —— 本文通篇引用的认证模式
