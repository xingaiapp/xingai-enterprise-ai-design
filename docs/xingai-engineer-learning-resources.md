# XingAI Engineer Learning Resources

Purpose: shared reading list for XingAI engineers building enterprise AI decision systems, agent workflows, MCP integrations, and safe tool-using product surfaces.

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
3. Read OpenAI function calling and tool docs to understand schema-first tool surfaces.
4. Read MCP introduction, then the MCP specification.
5. Read LangGraph only after you have a real stateful workflow need.
6. For Invest AI or broker-related work, read the XingAI ADRs before writing code.

## XingAI Engineering Notes

- Prefer workflow first, agent second. If the path is known, encode the workflow.
- A tool schema is product UX for the model. Name parameters clearly and include boundaries.
- MCP is an integration boundary, not a reason to move product decisions into request-time code.
- For Invest AI, do not put market/FRED/decision computation in FastAPI routes.
- Broker or trading tools are high-risk by default. Read-only comes first; writes require explicit gates and audit.
- Keep user-facing products as decision systems: one clear outcome, explainable next step, optional advanced agent behavior.

