# XingAI Enterprise AI Design

> From AI Demos to Enterprise AI Decision Systems

A collection of architectural patterns, frameworks, and best practices for building enterprise-grade AI systems that make better decisions.

**Bilingual posts:** Each article is **English** (`.md`) + **中文** (`.zh.md`)

## Education Guides

Hands-on learning tracks (concepts + labs). Index: [`guides/README.md`](guides/README.md).

Structured curriculum (levels 0–9): [`courses/README.md`](courses/README.md) · [中文](courses/README.zh.md).

Deep enterprise engineering track: [`deep-enterprise-ai/README.md`](deep-enterprise-ai/README.md) · [中文](deep-enterprise-ai/README.zh.md) · [runnable reference POC](enterprise-poc/README.md) · [中文](enterprise-poc/README.zh.md).

Program resources: [assessment framework](assessments/README.md) · [中文](assessments/README.zh.md) · [capstones](capstones/README.md) · [中文](capstones/README.zh.md) · [interview bank](interview-bank/README.md) · [中文](interview-bank/README.zh.md).

Shared engineer reference: [`docs/xingai-engineer-learning-resources.md`](docs/xingai-engineer-learning-resources.md) · [中文](docs/xingai-engineer-learning-resources.zh.md).

### Learning Product Boundary

This repository owns **educational source material and reference implementations** for AI engineers, architects, and CTOs. It is separate from [Learn AI](https://learn.xingai.app) ([`xingai-learn`](https://github.com/xingaiapp/xingai-learn)), the coding-interview **decision** product.

| Surface | Input | Primary outcome | Runtime ownership |
|---|---|---|---|
| Learn AI product | Coding interview question or screenshot | Next **coding pattern** to practice | [`xingai-learn`](https://github.com/xingaiapp/xingai-learn) |
| Foundation curriculum | AI engineering competency | Lesson, exercise, and **AI hiring-loop** gate | `courses/` |
| Deep enterprise curriculum | Enterprise architecture problem | Deep lab and review evidence | `deep-enterprise-ai/` |
| Reference POC | Lab requirements and simulated claims data | Tested production-shaped teaching implementation | `enterprise-poc/` |

**中文要点：** Learn AI（`learn.xingai.app`）根据一道编程面试题推荐下一步 Coding Pattern；本仓库的 `courses/` / `deep-enterprise-ai/` 教的是 AI 工程师到 CTO 的岗位能力与企业架构实验。二者数据库、进度模型、运行时互不合并。

Do not merge their databases, progress models, or runtime code. Learn AI may link to a relevant public lesson later, but the curriculum must not replace Learn AI's question → pattern → next-practice decision flow. Curriculum “interview” means **AI-role hiring loops** (system design, RAG, tools, governance)—not LeetCode pattern drills (those belong in Learn AI).

| Date | Title | Audience | Tags |
|------|-------|----------|------|
| 2026-07-12 | [MCP Auth from Robinhood — OAuth 2.1 / PKCE / Token Verification](guides/2026-07-12-mcp-oauth-auth-deep-dive.md) · [中文](guides/2026-07-12-mcp-oauth-auth-deep-dive.zh.md) | Engineers learning MCP auth | `mcp` `oauth` `pkce` `jwt` `education` |
| 2026-07-12 | [Build an OAuth 2.1 + PKCE MCP Project from Scratch](guides/2026-07-12-mcp-oauth-pkce-lab.md) · [中文](guides/2026-07-12-mcp-oauth-pkce-lab.zh.md) | Engineers implementing a demo Auth + MCP stack | `mcp` `oauth` `fastapi` `hands-on` `education` |

## Articles

| Date | Title | Audience | Tags |
|------|-------|----------|------|
| 2026-07-15 | [Anthropic's Loop Engineering Primer: Four Loop Types for Agent Work](articles/2026-07-15-anthropic-loop-engineering-getting-started.md) · [中文](articles/2026-07-15-anthropic-loop-engineering-getting-started.zh.md) | AI Architects, Platform Engineers, Tutor/Curriculum Authors | `architecture` `enterprise` `loop-engineering` `agents` `claude-code` `mcp` `education` `design-patterns` |
| 2026-07-15 | [Third-Party MCP Access: API Key or OAuth 2.1? A Decision Framework](articles/2026-07-15-third-party-mcp-auth-api-key-vs-oauth2.md) · [中文](articles/2026-07-15-third-party-mcp-auth-api-key-vs-oauth2.zh.md) | Enterprise Architects, AI Architects, Security Reviewers, Platform Engineers | `architecture` `enterprise` `mcp` `oauth` `api-design` `security` `third-party-integration` `design-patterns` |
| 2026-07-14 | [Redesigning the Agentic Claims Workflow: Fraud Sequencing, Escalation Routing, and Compliance Audit](articles/2026-07-14-claims-workflow-redesign-fraud-routing-audit.md) · [中文](articles/2026-07-14-claims-workflow-redesign-fraud-routing-audit.zh.md) | Enterprise Architects, AI Architects, Insurance Ops/Compliance | `architecture` `enterprise` `insurance` `claims` `agentic-ai` `workflow-design` `compliance` `audit-trail` `design-patterns` |
| 2026-07-13 | [MCP API Coverage vs. Workflow Tools: A Claims Partner Integration Case Study](articles/2026-07-13-mcp-api-coverage-vs-workflow-tools.md) · [中文](articles/2026-07-13-mcp-api-coverage-vs-workflow-tools.zh.md) | Enterprise Architects, AI Architects, Platform Engineers, Security | `architecture` `enterprise` `mcp` `api-design` `tool-gateway` `insurance` `claims` `design-patterns` |
| 2026-07-11 | [How MCP Works in Production: A Deep Dive from Robinhood Trading MCP](articles/2026-07-11-mcp-in-production-robinhood-case.md) · [中文](articles/2026-07-11-mcp-in-production-robinhood-case.zh.md) | Enterprise Architects, AI Architects, Platform Engineers, Security | `architecture` `enterprise` `mcp` `oauth` `agents` `tool-gateway` `governance` `broker-integration` `human-in-the-loop` |
| 2026-07-05 | [Agent Governance Reference Architecture: Authority, Provenance, Approval, Audit](articles/2026-07-05-agent-governance-reference-architecture.md) · [中文](articles/2026-07-05-agent-governance-reference-architecture.zh.md) | Enterprise Architects, Security Architects, AI Architects, Platform Engineers | `architecture` `enterprise` `agent-security` `governance` `human-in-the-loop` `prompt-injection` `audit` `policy-engine` |
| 2026-07-04 | [Executable Knowledge: Why Quality Increases Velocity in AI-Native Engineering](articles/2026-07-04-executable-knowledge-quality-velocity.md) · [中文](articles/2026-07-04-executable-knowledge-quality-velocity.zh.md) | Enterprise Architects, Engineering Managers, AI Architects, CTOs | `ai-native-engineering` `executable-knowledge` `claude-md` `skills` `mcp` `quality` `velocity` `knowledge-infrastructure` |
| 2026-07-03 | [Beyond Prompt Engineering: Why Enterprise AI Is a Runtime Problem](articles/2026-07-03-beyond-prompt-engineering-loop-engineering.md) · [中文](articles/2026-07-03-beyond-prompt-engineering-loop-engineering.zh.md) | Enterprise Architects, AI Architects, CTOs, Platform Engineers | `architecture` `enterprise` `loop-engineering` `context-engineering` `harness-engineering` `agent-runtime` `governance` `ai-platform` |
| 2026-07-03 | [From Prompt to Loop: AI-Native Architecture Evolution](articles/2026-07-03-prompt-to-loop-ai-native-architecture.md) · [中文](articles/2026-07-03-prompt-to-loop-ai-native-architecture.zh.md) | Enterprise Architects, AI Architects, CTOs | `architecture` `enterprise` `loop-engineering` `ai-native` `17-layer` `micro-loop-engine` `decision-os` |
| 2026-06-13 | [Orchestrator vs MCP Gateway: Why Enterprise AI Does Not Need an Orchestration MCP](articles/2026-06-13-orchestrator-vs-mcp-gateway.md) · [中文](articles/2026-06-13-orchestrator-vs-mcp-gateway.zh.md) | Enterprise Architects, AI Architects, Platform Engineers | `architecture` `enterprise` `mcp` `agent-orchestration` `tool-gateway` `governance` |
| 2026-06-07 | [From AI Demos to Enterprise AI Decision Systems: Why LLM + RAG + MCP Is Not Enough](articles/2026-06-07-enterprise-ai-decision-systems.md) · [中文](articles/2026-06-07-enterprise-ai-decision-systems.zh.md) | Enterprise Architects, AI Architects, CTOs | `architecture` `enterprise` `ai-decision-systems` `design-patterns` `mcp` `event-bus` `human-in-the-loop` |

## What This Repository Is

A **professional technical resource** for:

- **Enterprise Architects** — Understanding how to structure AI systems at scale
- **AI Architects** — Moving beyond demos to production-grade architectures
- **CTOs** — Making informed decisions about AI infrastructure
- **Engineering Managers** — Leading teams building enterprise AI
- **Senior Developers** — Building the systems that power enterprise AI

## What This Repository Is NOT

- A marketing blog or sales pitch
- Academic research papers
- A substitute for official MCP / OAuth RFCs or vendor docs
- Investment advice

Education guides under [`guides/`](guides/) teach protocol mechanics with labs; architecture articles under [`articles/`](articles/) stay aimed at enterprise decision-makers.

## Core Concepts

### The Evolution

```
AI Chatbot
    ↓
RAG System
    ↓
AI Agent
    ↓
Multi-Agent System
    ↓
AI Decision System
```

### The Maturity Model

| Level | Stack | Use Case | Enterprise Ready |
|-------|-------|----------|------------------|
| 1 | LLM + API | Demos, Learning | ❌ |
| 2 | LLM + RAG | MVP, Proof of Concept | ⚠️ |
| 3 | LLM + RAG + MCP | Single Agent System | ⚠️ |
| 4 | LLM + Event Bus + Agent Orchestration | Multi-System Integration | ✅ |
| 5 | Full Enterprise AI Decision System | Production at Scale | ✅ |

## XingAI's Position

We build **AI Decision Systems for Everyday Life** — focused tools that help people make better decisions in:

- **Health** — Meal Coach
- **Finance** — Invest AI
- **Travel** — Travel AI
- **Education (learners)** — Learn AI (coding-interview patterns), Research AI, SAT AI
- **Lifestyle** — Outfit AI, Routine AI

This repository shares the **architectural thinking and engineer curriculum** behind those systems. It is not Learn AI’s runtime.

## Key Articles Coming

- ~~Multi-Agent Orchestration vs MCP Gateway~~ → [Published 2026-06-13](articles/2026-06-13-orchestrator-vs-mcp-gateway.md)
- ~~Loop Engineering & AI-Native Platform Architecture~~ → [Published 2026-07-03](articles/2026-07-03-beyond-prompt-engineering-loop-engineering.md)
- ~~MCP in Production (Robinhood case)~~ → [Published 2026-07-11](articles/2026-07-11-mcp-in-production-robinhood-case.md)
- ~~MCP OAuth / PKCE education guides~~ → [Published 2026-07-12](guides/README.md)
- Event Bus Patterns in Enterprise AI
- Memory Architectures for AI Agents
- Human-in-the-Loop Decision Systems
- Security & Governance in Enterprise AI
- Cost Optimization at Scale
- Multi-Agent Orchestration Patterns → see [Orchestrator vs MCP Gateway](articles/2026-06-13-orchestrator-vs-mcp-gateway.md)

## Contributing

See [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) for guidelines.

## Bilingual Posts Convention

See [docs/BILINGUAL-POSTS.md](docs/BILINGUAL-POSTS.md) for how we maintain English + Chinese versions.

## Links

- [XingAI.app](https://xingai.app)
- [Tech Blog](https://github.com/xingaiapp/xingai-tech-blog)
- [GitHub](https://github.com/xingaiapp)
- [LinkedIn](https://www.linkedin.com/in/xingaiapp/)
- [Twitter](https://x.com/XingAIApp)

## License

Content is published under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). You're free to share and adapt with attribution.

---

**Author:** Xing Wang, AI Architect  
**Brand:** XingAI  
**Updated:** July 16, 2026
