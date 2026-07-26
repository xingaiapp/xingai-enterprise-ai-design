---
title: Evidence Engine + Eval Registry — 引用验证与 EEE 回归门禁
author: Xing Wang
date: 2026-07-26
tags: [architecture, enterprise, evidence, evaluation, eee, worker-cache, governance, citation-verification, design-patterns]
description: XingAI 如何把引用验证算力放在 Evidence Engine，把评估记录与 CI 回归门禁放在 EEE 形态的 Eval Registry，而不是塞进仪表盘或另造 schema。
---

# Evidence Engine + Eval Registry：引用验证与 EEE 门禁

研究和理赔团队常问同一件事：

> *用 LLM 做完引用验证之后，分数存在哪？怎样避免「这次 demo 很好、下周悄悄变差」？*

**简短回答：** **验证算力**放在 Evidence Engine（Worker 拥有逻辑；API 只读缓存）。**评估记录**放在 Eval Registry（EEE 形文件 + `diff --fail-on-regression`）。不要把记分板塞进仪表盘，也不要另造一套 schema。

![Evidence Engine + Eval Registry — System Design UX](../assets/evidence-engine-eval-registry-system-design-ux.png)

---

## 5W 框架

### What（这是什么？）

两个仓库，一条「验证 → 评估」闭环：

| 层 / 组件 | 角色 | 编排 / 拥有 |
|---|---|---|
| **evidence-worker** | 摄入 Markdown/URL、抽 Claim、查信源、可选 LLM 支持度检查、算指标 | 全部算力（原则 1） |
| **SQLite 缓存** | 仪表盘/API 的跨进程交接 | 键 `v1:verify:{id}`、`v1:eval:{case}` |
| **FastAPI + 本地仪表盘** | 只读查看已缓存项目 | 从不抓取、不调 LLM |
| **EEE 导出（`*.eee.json`）** | 可移植的评估 case | Schema `eee-2026.07-xingai.1` |
| **eval-registry** | 校验、存档、list/show、**diff** | 私有 `data/` + CI 退出码 |

**本文 Phase 1 不覆盖：** 托管 `*.xingai.app` 产品 UI、PDF 摄入、反证检索、多租户鉴权、用 MCP Gateway 拉引用页。

### Who（谁该读？）

- **企业 / AI 架构师** — Worker/Cache 边界与评估门禁落点
- **工程经理** — 哪些是 demo 可用、哪些已接近生产形态
- **平台 / CI 负责人** — `--fail-on-regression` 如何变成门禁
- **产品 / 研究负责人** — 「引用覆盖率」到底量什么
- **安全评审** — SSRF 防护、私有评估数据、EEE 里不放密钥

### Why（为什么重要？）

若不做拆分：

- 仪表盘变成**真相源** → 没有可持久、可 git diff 的评估史
- 团队各造**一次性 JSON 记分板** → Research AI / Claims / SAT 无法横向对比
- 绝对 Claim 计数进 CI → 文档一变长就「质量下跌」
- LLM 验证跑完**没有回归门禁** → 质量悄悄漂移

按本设计：

- 一套与 EvalEval 生态对齐的 **EEE** 形态
- Worker 算力可私有；Registry 数据保持**私有文件**
- 比率指标驱动门禁（`citation_coverage`、`unsupported_claim_rate`、`unverifiable_rate`）
- 本地仪表盘只是**查看器**，不是数据库

### When（何时需要？）

| 阶段 | 你需要什么 |
|---|---|
| **MVP / demo** | Worker `--no-llm --no-network` + fixture Markdown + report.md |
| **Phase 1 — 验证（今天）** | 完整 Worker + 缓存 + 本地仪表盘 + EEE → registry `diff` |
| **Phase 2 — 产品表面** | Research AI / Claims UI；公开展示静态导出；更多消费方 |
| **生产** | 私有评估存储位置、留存、API 鉴权、成本记账 |

**原则：** 先把**门禁**（EEE + diff）做实，再打磨**产品 UI**。没有回归存储的漂亮仪表盘只是 demo，不是平台。

### Where（落在架构哪一层？）

```text
┌─────────────────────────────────────┐
│  作者 / 操作者                        │
│  Markdown · URL · fixtures          │
└──────────────────┬──────────────────┘
                   ▼
┌─────────────────────────────────────┐
│  evidence-worker（算力）              │  ← 内部系统 A
│  摄入 → 抽取 → 验证 → 指标            │
└──────────┬───────────────┬──────────┘
           │               │
           ▼               ▼
   out/*.md|json|eee    cache.sqlite
           │               │
           │               ▼
           │        FastAPI（只读）→ 本地仪表盘
           ▼
┌─────────────────────────────────────┐
│  eval-registry（治理存储）            │  ← 内部系统 B
│  add · list · show · diff / CI      │
└─────────────────────────────────────┘
```

---

## 如何工作

### 端到端流程

```text
verify CLI → 产物 + 缓存 →（可选）仪表盘
                ↓
           *.eee.json → registry add → 之后: diff --fail-on-regression
```

### 组件职责

| 组件 | 输入 | 输出 | 工具 / 依赖 |
|---|---|---|---|
| 摄入 | 路径或 URL | Markdown 文本 + 信源 | httpx；私有主机 SSRF 拦截 |
| 抽取 | Markdown | Claims（可选 LLM） | Anthropic / OpenAI 可选 |
| 验证 | 信源 + Claims | 判定 + 证据摘录 | 抓取 + `complete_json` |
| 报告 / 指标 | Project | 覆盖率 + 比率 | 仅事实性分母 |
| EEE 导出 | EvaluationCase | 门禁比率 + config 中的计数 | Pydantic |
| Registry | EEE JSON | `data/` 下文件 | 原子写入 |
| Diff | 两条记录 | 增量 + `regressions[]` | 用旧跑的 `higher_is_better` |

### 示例：Radar fixture 跑数

`fixtures/2026-07-26-radar.md` 的典型 Phase 1 时间线：

```text
Step 1 · 摄入   · 解析链接定义     · ~40ms  · N 个信源
Step 2 · 抽取   · Claim 块         · ~100ms · 事实 vs 意见
Step 3 · 信源   · HTTP 可达性      · 数秒   · 可达 / 被墙 / 失效
Step 4 · 验证   · LLM 支持度       · 数十秒 · 多引用取最差判定
Step 5 · 导出   · 报告 + EEE + 缓存 · ~20ms  · metrics 仅比率
Step 6 · Registry · add + 与上次 diff · <10ms · 覆盖率下降则 FAIL
```

**锁定门禁指标：**

| 指标 | 公式 | 方向 |
|---|---|---|
| `citation_coverage` | 有引用的事实 Claim / 事实 Claim | 越高越好 |
| `unsupported_claim_rate` | (not_supported + uncited) / 事实 Claim | 越低越好 |
| `unverifiable_rate` | unverifiable / 事实 Claim | 越低越好 |

绝对计数（`supported`、`partial` 等）放在 `configuration.counts`，避免文档长短误触发 CI。顶层 `latency_seconds` 由 registry 对比（越低越好）。

**关键判定规则：** 多引用冲突时，**最差支持判定优先** — 反驳页不会被支持页盖住。

---

## 企业模式映射

| 模式 | 本设计如何落地 |
|---|---|
| **Worker / Cache 边界** | Worker 写缓存；FastAPI 只 `cache_get` — 与 invest-ai 同一原则 1 |
| **LLM 前先确定性层** | 无 Key 也可解析 + 可达性；LLM 是可选层 |
| **Trace / 治理** | Project JSON + EEE 四区块是持久审计形态 |
| **Orchestrator vs MCP Gateway** | Worker **不是** MCP；引用抓取是带 SSRF 防护的直连 HTTP。域 MCP（若有）属 Phase 2+ |
| **分阶段路线** | Phase 1 验证「验证 + 评估门禁」；Phase 2 挂产品 UI 与更多消费方 |
| **可观测性** | 指标是带语义（`higher_is_better`）的一等公民比率，不是藏起来的思维链 |

---

## 反模式

| 反模式 | 为何失败 | 应改为 |
|---|---|---|
| 仪表盘当真相源 | 无持久历史；难进 CI | EEE 文件进 eval-registry |
| 绝对计数进 CI 门禁 | 文档长短伪装成质量变化 | metrics **只导出比率** |
| 多引用取最好 | 一条好引用掩盖矛盾 | 最差支持判定优先 |
| `datetime.UTC` / 弱路径 id | 3.10 挂掉；`--project ../x` 逃逸 | `timezone.utc`；强制 slug + 限制在 `--out` 下 |
| 另造评估 JSON schema | 无法生态复用 | 坚持 EEE 四区块 |
| API 重新跑验证 | 违反原则 1；成本与风险翻倍 | 只让 Worker 算；API 只读 |
| 把被墙 URL 当空成功 | 静默 0 Claim「成功」 | 摄入被墙/空正文时直接报错 |

---

## POC / 平台映射

| 企业概念 | Phase 1（今天） | Phase 2+ |
|---|---|---|
| 引用验证引擎 | `xingai-evidence-engine` Worker + 本地 UI | Research AI Evidence Workspace；Claims B2B 表面 |
| 评估存储 / CI 门禁 | `xingai-eval-registry` CLI + 私有 `data/` | 共享私有存储；更多 harness（SAT AI 等） |
| Schema | EEE `eee-2026.07-xingai.1` | 随 EvalEval 生态稳定向上对齐 |
| 公开展示 | xingai.app 目录卡片；可选静态 `evidence-demo/` | 托管产品鉴权与租户 |
| 成本 / Token 记账 | `cost_usd` 可空 | 从供应商用量回填 |

仓库：

- [xingai-evidence-engine](https://github.com/xingaiapp/xingai-evidence-engine) — [用户指南](https://github.com/xingaiapp/xingai-evidence-engine/blob/main/docs/guides/user-guide.zh.md)
- [xingai-eval-registry](https://github.com/xingaiapp/xingai-eval-registry) — [用户指南](https://github.com/xingaiapp/xingai-eval-registry/blob/main/docs/guides/user-guide.zh.md)

---

## 相关文档

- [ADR-001 — 一套引擎，两个产品（Evidence）](https://github.com/xingaiapp/xingai-evidence-engine/blob/main/docs/adr/001-one-engine-two-products.zh.md)
- [ADR-001 — EEE 记录形态（Registry）](https://github.com/xingaiapp/xingai-eval-registry/blob/main/docs/adr/001-eee-record-shape.zh.md)
- [Orchestrator vs MCP Gateway](2026-06-13-orchestrator-vs-mcp-gateway.zh.md) — 编排 ≠ 工具网关
- [Agent Governance 参考架构](2026-07-05-agent-governance-reference-architecture.zh.md) — 出处 / 审计心智
- Every Eval Ever — [IBM Research](https://research.ibm.com/blog/every-evaluation-ever) / [EvalEval](https://evalevalai.com/projects/every-eval-ever/)

---

**作者：** Xing Wang  
**发布：** 2026-07-26  
**标签：** architecture, enterprise, evidence, evaluation, eee, worker-cache, governance
