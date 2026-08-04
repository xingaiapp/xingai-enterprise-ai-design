---
title: 每日投资智报 — 在 Invest AI 内由 Worker 拥有的中文 PDF
author: Xing Wang
date: 2026-08-04
tags: [architecture, invest-ai, reporting, worker-cache, pdf, resend, design-patterns]
description: 为什么 XingAI 把每日投资智报做成 Invest AI 的 Worker 包而非绿场报告产品，以及 live K 线、N/A 诚实与 Resend 如何落在决策缓存边界上。
---

# 每日投资智报：在 Invest AI 内由 Worker 拥有的中文 PDF

> *一份密排中文 A4 投资 PDF，该做成新产品，还是挂在已发送 Premium Daily Brief 的 Worker 上？*

**短答：** 扩展 Invest AI。ADR-032 已禁止绿场日报栈；ADR-040 对**每日投资智报**同规则。Worker 拥有快照 → 计算 → PDF → 邮件；FastAPI 只登记报告类型。

![每日投资智报 — 系统设计 UX](../assets/daily-investment-zhibao-system-design-ux.png)

---

## 5W 框架

### What（这是什么？）

| 层 / 组件 | 角色 | 拥有 |
|---|---|---|
| **CLI / 调度** | `validate-data` → `generate` → `send` / `run-daily` | 操作入口 |
| **报告目录** | 类型 `daily-investment-zhibao` | FastAPI 元数据（ADR-025） |
| **investment_zhibao 包** | 配置、yfinance、计算/风险/建议、ReportLab A4、Resend | 全部决策与投递计算 |
| **配置** | `user.yaml`、`portfolio.csv`、`policy.yaml` | 持仓与策略 — 不编造权重 |
| **投递** | `output/pdf/`；邮件 dry-run/send | 与其他 Invest 摘要相同的 Resend 密钥 |

**范围外：** 新 `*.xingai.app`、当前用 XNP 传输、编造 CAPE、自动交易。

### Who（谁该读？）

- **产品 / 运维** — 哪些日报邮件存在、归哪个仓
- **架构师** — 为何 Plan A（扩展）优于旁路报告仓
- **Worker 工程师** — 包布局与缺失基本面的诚实规则
- **安全** — 仓内无密钥；主机有 Resend 前保持 dry-run

### Why（为何重要？）

没有 Plan A：

- 重复的 Resend + PDF 栈会与 Premium Brief 语义漂移
- 假 CAPE 看起来「高级」但摧毁信任
- XNP 在还不能发送时就被当成投递方

有了 Plan A：

- Invest 报告边界留在一个 monorepo
- Live K 线写入真实 `market_as_of`；缺指标保持 `N/A`
- 将来换 XNP 只是传输变更

### When（何时需要？）

| 阶段 | 需要什么 |
|---|---|
| MVP | Mock 快照 + PDF 结构 + dry-run 邮件 |
| Live | 批量 Yahoo K 线、日涨跌、截止日诚实 |
| Ops | `run-daily` 定时 + Worker 上的 Resend |
| Phase 2+ | 更富基本面、更密 PDF、可选 XNP |

**规则：** 缺数据 = `N/A`。永不发明可交易精度。

### Where（在架构何处？）

```text
操作者 / Cron
    → investment_zhibao CLI（worker）
        → 配置 + yfinance
        → 计算 / 风险 / 建议
        → 中文 A4 PDF
        → Resend（dry-run | send）
    → FastAPI 报告目录（仅元数据）
```

---

## 如何工作

### 端到端

```text
加载配置 → 拉 K 线 → 快照 → PDF → 邮件 → 产物
```

### 企业模式与反模式

- Worker / 缓存边界；分阶段诚实；扩展优先于绿场
- 反模式：为版式开新仓、编 CAPE、把 PDF 生成挪进 FastAPI、在 Phase 2 无通道时宣称 XNP「已上线」

---

## 相关文档

- [ADR-040](https://github.com/xingaiapp/xingai-invest-ai/blob/main/docs/adr/040-daily-investment-zhibao-pdf.md)
- Tech blog：`xingai-tech-blog/posts/2026-08-04-invest-ai-daily-investment-zhibao-pdf.md`
