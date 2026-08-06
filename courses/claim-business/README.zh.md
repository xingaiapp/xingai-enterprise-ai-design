# 理赔业务课程（Claim Business）

面向 IT 解决方案架构师与软件工程师的完整双语培训：在缺乏保险业务背景的前提下，学习设计理赔系统（Property / CTABS 风格、Sedgwick 风格 TPA 合作），并把业务接到可审计的系统设计。

## 文档

| 语言 | 文件 |
|------|------|
| English | [claim-business-guide-en.md](./claim-business-guide-en.md) |
| 简体中文 | [claim-business-guide-zh.md](./claim-business-guide-zh.md) |

两份为完整对等件（Level 1–6、Lifecycle、Property 深潜、工伤对照、TPA/RACI、架构/DDD/API、案例、术语表、测评、30/60/90）。中文首次术语格式：`理赔员（Claims Adjuster）`。

## 受众

- 熟悉 Azure / .NET / API / 事件驱动的资深工程师与架构师
- 尚不熟悉理赔术语、Adjuster 作业、准备金、支付、TPA 模式
- 可能参与 Sedgwick 风格 Property / CTABS 项目

## 准确性立场

教材讲授**行业通识**、**典型 TPA 模式**与**示意架构**。**不是** Sedgwick 机密流程、库表、内部 API 或客户专属规则。实际以 Client Instructions、Service Agreements、Policy、管辖区与 Delegated Authority 为准。Sedgwick 通常是 **TPA / 理赔管理合作方**，不必然是 Insurance Carrier。

## 学习建议

1. 先读开篇与一页心智模型  
2. 完成 Level 1–2 再进架构章  
3. 手算走完 Property 案例的 Reserve / Payment  
4. 做工坊后再写 ADR / 方案  
5. 30 题测评建议 ≥80% 过闸  

## Level 地图

| Level | 焦点 |
|-------|------|
| 1 | 词汇与组织角色 |
| 2 | Claim Lifecycle |
| 3 | Adjuster 作业 |
| 4 | 财务、法律与运营控制 |
| 5 | 方案与需求转化 |
| 6 | 可扩展、可审计、可配置平台架构 |
