# XingAI Engineer Learning Resources

Chinese: [xingai-engineer-learning-resources.zh.md](xingai-engineer-learning-resources.zh.md)

Purpose: shared reading list for XingAI engineers building enterprise AI decision systems, agent workflows, MCP integrations, and safe tool-using product surfaces.

Version-sensitive references last verified: July 15, 2026.

Audience:

- XingAI engineers
- Cursor / Codex / agent workflow authors
- Enterprise AI architects and platform engineers

Use this as a foundation before designing agentic features. For XingAI products, remember the product rule: decision systems first, chat/agents only when they improve the main decision path.

## Core Agent Foundations

| Priority | Resource | Why it matters for XingAI |
|---|---|---|
| Required | [Yao et al. (2022), ReAct: Synergizing Reasoning and Acting in Language Models](https://arxiv.org/abs/2210.03629) | Foundational pattern for reasoning + acting loops: observe, reason, call tools, update state. |
| Required | [Anthropic, Building Effective AI Agents](https://www.anthropic.com/engineering/building-effective-agents) | Practical distinction between workflows and agents; useful guardrail against overbuilding. |
| Required | [Anthropic Docs, How tool use works](https://platform.claude.com/docs/en/agents-and-tools/tool-use/how-tool-use-works) | Explains client-driven tool loops and how a model emits tool-use requests. |
| Required | [OpenAI API Docs, Function calling](https://developers.openai.com/api/docs/guides/function-calling) | Structured schema design for tool calls and strict arguments. |
| Required | [OpenAI API Docs, Tools](https://developers.openai.com/api/docs/guides/tools) | Current OpenAI tool surface, including hosted tools and MCP/connectors references. |
| High | [Anthropic / Claude Code, Loop engineering: Getting started with loops](https://claude.com/blog/getting-started-with-loops) | Defines agentic loops as repeat-until-stop-condition work, and how turn-based, goal-based, time-based, and proactive loops differ — pairs with XingAI Loop Engineering articles. |
| High | [XingAI reading note: Anthropic's Loop Engineering Primer](../articles/2026-07-15-anthropic-loop-engineering-getting-started.md) · [中文](../articles/2026-07-15-anthropic-loop-engineering-getting-started.zh.md) | Tutorial-oriented walkthrough of the four loop types, plus the Prompt → MCP → Loop reading timeline. |

## Protocols And Interoperability

| Priority | Resource | Why it matters for XingAI |
|---|---|---|
| Required | [Model Context Protocol specification](https://modelcontextprotocol.io/specification) | Official MCP protocol reference for connecting LLM apps to tools, resources, prompts, and external context. |
| Required | [Model Context Protocol introduction](https://modelcontextprotocol.io/introduction) | Faster conceptual entry point before reading the full spec. |
| High | [A2A Protocol specification](https://a2a-protocol.org/latest/specification/) | Agent-to-agent interoperability; useful when thinking beyond one app/tool boundary. |
| High | [A2A GitHub repository](https://github.com/a2aproject/A2A) | Reference implementation, examples, and active protocol development. |

## Agent Frameworks And Workflows

| Priority | Resource | Why it matters for XingAI |
|---|---|---|
| High | [LangGraph overview](https://docs.langchain.com/oss/python/langgraph/overview) | Stateful, long-running workflow/agent orchestration with persistence and human-in-the-loop design. |
| High | [LangGraph workflows + agents](https://docs.langchain.com/oss/python/langgraph/workflows-agents) | Useful for deciding when to model a feature as a graph workflow. |
| Medium | [AutoGen documentation](https://microsoft.github.io/autogen/stable/) | Multi-agent collaboration patterns; useful reference, but not a default dependency. |

## Models, Retrieval, Security, And Governance

| Priority | Resource | Why it matters for XingAI |
|---|---|---|
| Required foundation | [Vaswani et al. (2017), Attention Is All You Need](https://arxiv.org/abs/1706.03762) | Transformer architecture foundation for modern LLMs. |
| Required for RAG | [Lewis et al. (2020), Retrieval-Augmented Generation](https://arxiv.org/abs/2005.11401) | Foundational retrieval-plus-generation architecture and evaluation framing. |
| Required for production | [NIST AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework) | Lifecycle risk framework organized around Govern, Map, Measure, and Manage. |
| Required for generative AI | [NIST Generative AI Profile](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf) | Generative-AI-specific risks and actions for governance, provenance, testing, and incident disclosure. |
| Required for security | [OWASP GenAI Security Project](https://genai.owasp.org/) | Application-security risks and mitigations for LLM and agent systems. |

## XingAI-Specific MCP And Safety References

| Priority | Resource | Why it matters for XingAI |
|---|---|---|
| Required for Invest AI | [`xingai-invest-ai/docs/adr/012-decision-cache-boundary.md`](../../xingai-invest-ai/docs/adr/012-decision-cache-boundary.md) | FastAPI reads cache; worker/core owns investment decision computation. |
| Required for Invest AI MCP | [`xingai-invest-ai/docs/adr/003-mcp-phased-rollout.md`](../../xingai-invest-ai/docs/adr/003-mcp-phased-rollout.md) | Defines phased MCP rollout from data MCPs to high-risk broker execution. |
| Required for Robinhood MCP | [`xingai-invest-ai/docs/wiki/robinhood-agentic-trading-mcp.md`](../../xingai-invest-ai/docs/wiki/robinhood-agentic-trading-mcp.md) | Internal reference for Robinhood Trading MCP, OAuth/auth flow, tool catalog, and platform setup. |
| Required for Robinhood MCP | [`xingai-invest-ai/docs/adr/028-robinhood-mcp-execution-gates.md`](../../xingai-invest-ai/docs/adr/028-robinhood-mcp-execution-gates.md) | Execution gates for any `place_*` MCP tool: human confirmation, freshness, audit, Agentic account only. |

## Suggested Reading Order

1. Read ReAct to understand the basic agent loop.
2. Read Anthropic's agent article to separate deterministic workflows from autonomous agents.
3. Read [Getting started with loops](https://claude.com/blog/getting-started-with-loops) for concrete loop types (turn / goal / time / proactive) and stop conditions.
4. Read OpenAI function calling and tool docs to understand schema-first tool surfaces.
5. Read MCP introduction, then the MCP specification.
6. Read LangGraph only after you have a real stateful workflow need.
7. For Invest AI or broker-related work, read the XingAI ADRs before writing code.
8. Pair the Claude loops guide with XingAI's [Beyond Prompt Engineering → Loop Engineering](../articles/2026-07-03-beyond-prompt-engineering-loop-engineering.md) and [Prompt to Loop architecture](../articles/2026-07-03-prompt-to-loop-ai-native-architecture.md) for the platform framing.
9. Before production release, apply NIST lifecycle governance and perform a dedicated OWASP-aligned security review.

## XingAI Engineering Notes

- Prefer workflow first, agent second. If the path is known, encode the workflow.
- Prefer the simplest loop that fits: turn-based for one-off tasks; goal-/time-based only when stop conditions and verification are clear (see Anthropic's loops guide).
- A tool schema is product UX for the model. Name parameters clearly and include boundaries.
- MCP is an integration boundary, not a reason to move product decisions into request-time code.
- For Invest AI, do not put market/FRED/decision computation in FastAPI routes.
- Broker or trading tools are high-risk by default. Read-only comes first; writes require explicit gates and audit.
- Keep user-facing products as decision systems: one clear outcome, explainable next step, optional advanced agent behavior.

## Quick Resource List

### AI And Agent Foundations

1. [Attention Is All You Need](https://arxiv.org/abs/1706.03762) — Transformer and modern LLM foundations.
2. [ReAct: Synergizing Reasoning and Acting](https://arxiv.org/abs/2210.03629) — The reasoning-and-action Agent Loop.
3. [Anthropic: Building Effective AI Agents](https://www.anthropic.com/engineering/building-effective-agents) — Workflows versus autonomous agents.
4. [Anthropic: How Tool Use Works](https://platform.claude.com/docs/en/agents-and-tools/tool-use/how-tool-use-works) — Client-driven tool-calling loops.
5. [Anthropic: Getting Started with Loops](https://claude.com/blog/getting-started-with-loops) — Turn-based, goal-based, time-based, and proactive loops.
6. [OpenAI: Function Calling](https://developers.openai.com/api/docs/guides/function-calling) — Structured tool definitions and arguments.
7. [OpenAI: Tools](https://developers.openai.com/api/docs/guides/tools) — OpenAI tools, hosted tools, connectors, and MCP.

### RAG And Knowledge Systems

8. [Retrieval-Augmented Generation](https://arxiv.org/abs/2005.11401) — Foundational RAG architecture and evaluation.

### Protocols

9. [MCP Introduction](https://modelcontextprotocol.io/introduction) — Beginner-friendly MCP overview.
10. [MCP Specification](https://modelcontextprotocol.io/specification) — Official protocol specification.
11. [A2A Protocol Specification](https://a2a-protocol.org/latest/specification/) — Agent-to-agent interoperability.
12. [A2A GitHub Repository](https://github.com/a2aproject/A2A) — Implementations and examples.

### Agent Frameworks

13. [LangGraph Overview](https://docs.langchain.com/oss/python/langgraph/overview) — Stateful and durable agent workflows.
14. [LangGraph Workflows and Agents](https://docs.langchain.com/oss/python/langgraph/workflows-agents) — Workflow, routing, and agent patterns.
15. [AutoGen Documentation](https://microsoft.github.io/autogen/stable/) — Multi-agent collaboration patterns.

### Security And Governance

16. [NIST AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework) — Govern, Map, Measure, and Manage AI risk.
17. [NIST Generative AI Profile](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf) — Generative AI governance, testing, provenance, and incidents.
18. [OWASP GenAI Security Project](https://genai.owasp.org/) — LLM and Agent application security risks.

### XingAI Internal References

19. [XingAI Loop Engineering Primer](../articles/2026-07-15-anthropic-loop-engineering-getting-started.md)
20. [Decision Cache Boundary](../../xingai-invest-ai/docs/adr/012-decision-cache-boundary.md)
21. [MCP Phased Rollout](../../xingai-invest-ai/docs/adr/003-mcp-phased-rollout.md)
22. [Robinhood Agentic Trading MCP](../../xingai-invest-ai/docs/wiki/robinhood-agentic-trading-mcp.md)
23. [Robinhood MCP Execution Gates](../../xingai-invest-ai/docs/adr/028-robinhood-mcp-execution-gates.md)
