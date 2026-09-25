# 从"玩具级 Demo"到"企业级 AI Agent"

单课程课，讲清楚"Demo 演示得好"和"系统能被运营"之间的差距。以 **Claims Copilot（理赔助手）** 为贯穿案例，但工程内容与行业无关。

## 文档

| 语言 | 文件 |
|------|------|
| English | [toy-demo-to-enterprise-agent-guide-en.md](./toy-demo-to-enterprise-agent-guide-en.md) |
| 简体中文 | [toy-demo-to-enterprise-agent-guide-zh.md](./toy-demo-to-enterprise-agent-guide-zh.md) |

两个版本是完整对等的同级文档。中文版技术术语首次出现时保留英文。

## 目标读者

- 已经会调 LLM API、但没做过生产 Agent 的工程师
- 正在准备 Agent 方向简历或系统设计面试的人
- 需要一套共同语言来判断"这东西能不能上线"的架构师

**不需要**：生产 Agent 经验、熟悉某个 Agent 框架、保险业务背景。

## 本课的核心论点

> 企业级不等于"技术栈更复杂"。企业级等于**为失败设计**。

本课用四个维度区分 Demo 与生产系统 —— Business Logic、System Architecture、Objective、Value Evaluation —— 并给出五阶段升级路径，每个阶段都带验收条件和常见翻车点。

## 最重要的一节

**§5.4 —— 分母必须可复现。**

绝大多数 Agent 课程会给出一张指标表（`Required Fact Coverage ≥95%`），却不追问 95% 的分母是什么。如果"哪些事实是必需的"由 LLM 判断，分母就会在两次运行之间漂移，指标无法用于回归检测。

这不是理论担忧：`xingai-evidence-engine` ADR-004 记录了实测结果 —— 同一份输入跑两次，因为 temperature 未显式设置，被判定为事实性陈述的句子数是 **4 条 vs 2 条**。

如果只读一节，读这一节。

## 目录

| § | 主题 |
|---|---|
| 1 | 四个关键区别，以及一个能立刻分辨 Demo 与生产的问题 |
| 2 | Business Logic —— 十步业务闭环，含失败与拒绝分支 |
| 3 | System Architecture —— 能力清单、幂等、On-Behalf-Of、Prompt Injection 防护 |
| 4 | Objective —— 什么时候**不该**用 Agent（决策树） |
| 5 | Value Evaluation —— Baseline、可复现的分母、评测集设计、真实 token 成本 |
| 6 | 五阶段升级路径与逐阶段验收条件 |
| 7 | Newbie → Expert 能力分级 |
| 8 | 简历项目验收表，以及面试官会追问什么 |
| 9 | 七个常见反模式 |
| 10 | 课后练习与完整答案，含越权/注入测试用例设计 |

## 相关 XingAI 材料

- 业务背景：[理赔业务完整课程](../claim-business/README.zh.md)
- 同一案例的 Agent 实现：[Claims Copilot Agent](../claims-copilot-agent/README.zh.md)
- 身份机制：[MCP OAuth 深度解析](../../guides/2026-07-12-mcp-oauth-auth-deep-dive.zh.md) · [PKCE 实验课](../../guides/2026-07-12-mcp-oauth-pkce-lab.zh.md)
- 课程契约：[../COURSE-STANDARD.zh.md](../COURSE-STANDARD.zh.md)

## 准确性边界

文中的架构图、API 形态、工具名、指标目标均为**示意性设计**（illustrative design），不描述任何实际生产系统。理赔业务示例沿用[理赔业务课程](../claim-business/README.zh.md)的准确性边界：真实流程取决于 Client Instructions、Service Agreement、保单条款、司法辖区与授权范围。不构成法律、合规或投资建议。
