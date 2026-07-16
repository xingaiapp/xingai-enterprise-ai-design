# XingAI AI Interview Bank

Chinese: [README.zh.md](README.zh.md)

Use questions as prompts, not scripts. Score the evidence, reasoning, correction behavior, and communication appropriate to the **AI engineering / architect / leadership role**.

This bank is for **hiring-loop practice**, not [Learn AI](https://learn.xingai.app) coding-pattern drills.

## Beginner

1. Explain training versus inference using a concrete example.
2. Implement cosine similarity and test zero vectors.
3. Explain precision, recall, and one case where accuracy misleads.
4. What is an embedding, and what does distance fail to prove?
5. Describe one project, its baseline, and one failure you found.

## AI Engineer

1. Design a typed LLM endpoint with timeout, retry, validation, and evaluation.
2. Debug a RAG system with relevant documents but unsupported answers.
3. Compare RAG, long context, search, fine-tuning, and deterministic lookup.
4. Design a tool schema and identify its authorization boundary.
5. Measure an agent beyond task completion rate.

## Senior And Staff

1. Design a durable agent workflow that survives restart and avoids duplicate writes.
2. Investigate an unsafe-action-rate regression after a model change.
3. Define SLOs, canary gates, observability, and rollback for an AI service.
4. Threat-model indirect prompt injection through retrieved documents and tools.
5. Explain when multi-agent design is worse than one workflow.

## Architect

1. Draw boundaries among domain APIs, MCP gateway, orchestrator, policy engine, and event bus.
2. Design a multi-tenant RAG platform with deletion, ACLs, provenance, and audit.
3. Separate decision computation, transport, explanation, approval, and execution.
4. Plan migration from an AI demo to a governed decision system.
5. Resolve disagreement between product velocity and security control requirements.

## CTO

1. Select and sequence ten AI opportunities with limited capital and uncertain benefits.
2. Define build/buy/partner criteria and a vendor exit strategy.
3. Design the AI operating model across platform, product, security, risk, and data teams.
4. Respond to a major AI incident in the first hour, first week, and next quarter.
5. Explain AI investment, residual risk, and kill criteria to the board.

## Follow-Up Pattern

For every answer ask: What assumption matters most? What baseline did you reject? How will you measure success? What fails first? Who owns the outcome? What changes at 10x scale? What would make you stop?

## Scoring Anchor

Weak answers list tools. Competent answers define requirements and a working baseline. Strong answers quantify tradeoffs, failures, and evidence. Exceptional answers adjust depth to the audience, surface uncertainty, establish ownership, and improve the problem framing without avoiding the question.

