---
title: Invest Lab 反馈环 — 先有纸面证据，再谈 draft
author: Xing Wang
date: 2026-08-05
tags: [architecture, invest-ai, investsim, mcp, robinhood, paper-trading, worker-cache, design-patterns]
description: Invest AI、InvestSim、Robinhood MCP 如何共用一条纸面到 draft 的环路：Worker 拥有 K 线与信号，实验室拥有 sleeve 与证据，MCP 在 fail-closed 下起草且不自动成交。
---

# Invest Lab 反馈环：先有纸面证据，再谈 draft

> *Invest AI 排名单、InvestSim 跑纸面、Robinhood MCP 起草订单——谁拥有真相，什么仍挡住自动成交？*

**短答：** Invest AI Worker 拥有行情写入（K 线、信号、纸面账本、Strategy Lab）。InvestSim 拥有多 sleeve 纸面证据与 `mcp-preferred`。Robinhood MCP fail-closed 消费证据，然后仍要人确认（G1–G7）。没有任何仓替别人调用 `place_*`。

![Invest Lab 反馈环 — 系统设计 UX](../assets/invest-lab-feedback-loop-system-design-ux.png)

---

## 5W 要点

| 仓 | 拥有 | 不拥有 |
|---|---|---|
| **xingai-invest-ai** | OHLCV（036）、事件（035）、纸面（037）、strategy-lab（038）、EEE（039）、情报报告（032–034、040） | 券商成交 |
| **invest-performance-sim** | 25 个纸面 sleeve（至 Tier-2.5 / ADR 0031）、execution evidence、clearance / mcp-preferred | 调用 Robinhood `place_*` |
| **xingai-robinhood-mcp** | Fail-closed 网关、signal_watcher draft、证据消费（010）、偏好实验室策略（011） | 因证据绿灯就软化 G1 |

**规则：** 证据合格管的是「能不能起草」——从不替代 G1。

## 反模式

- FastAPI 请求路径替程序化消费者直拉 Yahoo
- InvestSim 调用 `place_*`
- `eligible: true` 就自动批准
- 把 sleeve 数量增加当成每条策略已成熟

## 相关

- Invest AI ADR 032–040；InvestSim 0020、0024–0027、0030–0031；Robinhood MCP 010/011
- `xingai-tech-blog` 2026-08-05 系列
