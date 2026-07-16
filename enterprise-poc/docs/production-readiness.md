# Production Readiness Checklist

Chinese: [production-readiness.zh.md](production-readiness.zh.md)

No checklist grants production approval; named owners must attach evidence and accept residual risk.

- Identity: issuer/audience/signature/key rotation/workload identity verified.
- Authorization: tenant isolation, RBAC/ABAC/scopes, step-up, deny reasons, negative tests.
- Data: classification, consent, provenance, retention, deletion, backup, restore, encryption.
- RAG: ACL before ranking, retrieval/grounding evaluation, poisoning defense, stale semantics.
- Agents: bounded tools/steps/time/cost, typed handoffs, no-progress stop, human escalation.
- MCP: protected-resource metadata, resource indicators, audience binding, least privilege, approval.
- Security: threat model, red team, dependency/SBOM, secrets, egress, SSRF, incident process.
- Reliability: SLO/error budget, capacity, backpressure, idempotency, canary, rollback, RTO/RPO.
- Observability: redacted logs, metrics, traces, correlation, owned alerts, outcome monitoring.
- Audit: immutable storage, event schema, ordering, access, retention, verification, export.
- Evaluation: versioned representative/adversarial sets, human calibration, release gates, drift.
- Organization: accountable domain owner, SRE/support, legal/privacy/risk approval, training, kill criteria.

