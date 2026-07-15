# XingAI 工程师学习资源

English: [xingai-engineer-learning-resources.md](xingai-engineer-learning-resources.md)

用途：为构建企业 AI 决策系统、Agent Workflow、MCP 集成和安全工具调用产品的 XingAI 工程师提供共享阅读清单。

版本敏感资料最后核验日期：2026 年 7 月 15 日。

受众包括 XingAI 工程师、Cursor/Codex/Agent Workflow 作者、企业 AI 架构师与平台工程师。设计 Agentic 功能前应掌握这些基础。XingAI 产品优先建设决策系统，只有当 Chat/Agent 能改善主决策路径时才引入。

## Agent 核心基础

| 优先级 | 资源 | 对 XingAI 的意义 |
|---|---|---|
| 必读 | [ReAct](https://arxiv.org/abs/2210.03629) | 推理与行动 Loop 的基础模式。 |
| 必读 | [Building Effective AI Agents](https://www.anthropic.com/engineering/building-effective-agents) | 区分 Workflow 与 Agent，避免过度设计。 |
| 必读 | [Anthropic Tool Use](https://platform.claude.com/docs/en/agents-and-tools/tool-use/how-tool-use-works) | 理解客户端驱动 Tool Loop。 |
| 必读 | [OpenAI Function Calling](https://developers.openai.com/api/docs/guides/function-calling) | 结构化 Schema 与严格参数。 |
| 必读 | [OpenAI Tools](https://developers.openai.com/api/docs/guides/tools) | 当前工具能力与 MCP/Connector 边界。 |
| 高 | [Getting Started with Loops](https://claude.com/blog/getting-started-with-loops) | Turn、Goal、Time、Proactive Loop 与停止条件。 |
| 高 | [XingAI Loop Engineering 解读](../articles/2026-07-15-anthropic-loop-engineering-getting-started.zh.md) | Prompt → MCP → Loop 的学习时间线与四类 Loop 教程。 |

## 协议与 Framework

| 优先级 | 资源 | 对 XingAI 的意义 |
|---|---|---|
| 必读 | [MCP Specification](https://modelcontextprotocol.io/specification) | 工具、资源、Prompt 与外部上下文协议。 |
| 必读 | [MCP Introduction](https://modelcontextprotocol.io/introduction) | 完整规范前的概念入口。 |
| 高 | [A2A Specification](https://a2a-protocol.org/latest/specification/) | Agent-to-Agent 互操作边界。 |
| 高 | [LangGraph](https://docs.langchain.com/oss/python/langgraph/overview) | 有状态、持久化、人机闭环编排。 |
| 中 | [AutoGen](https://microsoft.github.io/autogen/stable/) | 多 Agent 模式参考，不是默认依赖。 |

## 模型、检索、安全与治理

| 优先级 | 资源 | 对 XingAI 的意义 |
|---|---|---|
| 基础必读 | [Attention Is All You Need](https://arxiv.org/abs/1706.03762) | Transformer 架构基础。 |
| RAG 必读 | [Retrieval-Augmented Generation](https://arxiv.org/abs/2005.11401) | 检索加生成架构与评估基础。 |
| 生产必读 | [NIST AI RMF](https://www.nist.gov/itl/ai-risk-management-framework) | Govern、Map、Measure、Manage 生命周期治理。 |
| 生成式 AI 必读 | [NIST Generative AI Profile](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf) | 治理、来源、测试和事故披露。 |
| 安全必读 | [OWASP GenAI Security Project](https://genai.owasp.org/) | LLM 与 Agent 应用安全风险。 |

## XingAI MCP 与安全参考

- [Decision Cache Boundary](../../xingai-invest-ai/docs/adr/012-decision-cache-boundary.md)：FastAPI 只读缓存，Worker/Core 负责决策计算。
- [MCP Phased Rollout](../../xingai-invest-ai/docs/adr/003-mcp-phased-rollout.md)：从数据 MCP 到高风险执行的分阶段路径。
- [Robinhood Agentic Trading MCP](../../xingai-invest-ai/docs/wiki/robinhood-agentic-trading-mcp.md)：OAuth/Auth、工具目录与平台设置。
- [MCP Execution Gates](../../xingai-invest-ai/docs/adr/028-robinhood-mcp-execution-gates.md)：写工具的人类确认、新鲜度与审计门禁。

## 阅读顺序

1. Transformer 与 ReAct。
2. Workflow 与 Agent、Loop 类型及停止条件。
3. Function Calling、Tool Use 与 Schema-first 边界。
4. MCP Introduction、Specification 与 Authorization。
5. 有真实状态需求后学习 LangGraph；有跨 Agent 边界后学习 A2A/AutoGen。
6. 生产前执行 NIST 生命周期治理和 OWASP 对齐安全评审。
7. Invest AI 或 Broker 工作在编码前必须阅读 XingAI ADR。

## XingAI 工程原则

- Workflow 优先，Agent 其次；已知路径直接编码。
- Tool Schema 是模型侧产品 UX，参数和边界必须清楚。
- MCP 是集成边界，不是把决策移入请求时计算的理由。
- 交易工具默认高风险；先只读，写操作必须审批与审计。
- 用户产品保持为决策系统：明确结果、可解释下一步、可选高级 Agent 行为。
