---
title: Evidence 诚实栈 — Overlay、PDF 参考文献与引用日期
author: Xing Wang
date: 2026-08-04
tags: [architecture, evidence, provenance, worker-cache, governance, pdf, design-patterns]
description: Evidence Engine ADR-009～011 如何用独立 overlay 键、仅 URL/DOI 的数字参考文献、以及页面/arXiv 日期，避免假 provenance 与被改写的 verify 缓存。
---

# Evidence 诚实栈：Overlay、PDF 参考文献与引用日期

> *引用校验能跑之后，还有什么会让研究产品不诚实？*

**短答：** 为人审改写 verify 缓存、发明 PDF 覆盖率或参考文献链接、以及报告无法证明的「公告→论文」间隔。ADR-009～011 用独立 overlay 键、仅 URL/DOI 的数字参考文献、以及不发明 lag 指标的日期列来修补。

![Evidence 诚实栈 — 系统设计 UX](../assets/evidence-honesty-overlay-system-design-ux.png)

---

## 5W 框架

### What

| 决策 | ADR | 拥有 |
|---|---|---|
| 人审 / skill 批准 / 回归 schema | 009 | `v1:review:`、`v1:skill:`、run/experience |
| 数字 PDF 参考文献 → Sources | 010 | 仅 URL/DOI；作者-年份 unresolved |
| 报告上的引用日期 | 011 | `page_date`；仅 arXiv 的 `first_public` |

Worker 仍拥有校验计算。API 在读时合并 overlay。公开 demo 保持静态（ADR-002）。

### Why

没有这些 ADR：再跑 verify 抹掉 Accept；PDF 覆盖率撒谎；雷达把爬取日说成「今日」。

有了它们：overlay 留下；仅可抓取参考文献进入校验；日期仅信息展示——引用旧作不是门控失败。

### Rule

不要带着脚注免责声明，去发一个自信错误的数字。

---

## 反模式

- 原地 PATCH verify
- 模糊作者-年份对齐到参考文献
- 已批准 skill 自动合进抽取器
- LLM 决定的「首次公开」日期

---

## 相关

- Evidence Engine ADR-009 / 010 / 011
- 模式：`human-overlay-cache`
- 前文：[Evidence Engine + Eval Registry](2026-07-26-evidence-engine-eval-registry.md)
