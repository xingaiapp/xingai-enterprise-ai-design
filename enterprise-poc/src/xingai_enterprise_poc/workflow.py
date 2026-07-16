from uuid import uuid4

from .agents import FraudSpecialist, PolicySpecialist, consensus
from .audit import AuditLedger
from .loops import LoopState, WorkflowState
from .models import Decision, DecisionStatus, RequestContext, Risk
from .observability import Telemetry
from .rag import AuthorizedRetriever


class ClaimsDecisionWorkflow:
    def __init__(
        self,
        retriever: AuthorizedRetriever,
        audit: AuditLedger,
        telemetry: Telemetry,
    ) -> None:
        self.retriever = retriever
        self.audit = audit
        self.telemetry = telemetry
        self.policy_specialist = PolicySpecialist()
        self.fraud_specialist = FraudSpecialist()

    def propose(self, claim_id: str, claim_amount: float, context: RequestContext) -> Decision:
        loop = LoopState()
        with self.telemetry.trace("claim.propose", context.correlation_id):
            loop.transition(WorkflowState.RESEARCH)
            evidence = self.retriever.retrieve(f"claim policy coverage {claim_id}", context)
            loop.transition(WorkflowState.REVIEW)
            findings = (
                self.policy_specialist.review(evidence),
                self.fraud_specialist.review(claim_amount, evidence),
            )
            risk = consensus(findings)
            requires_approval = risk == Risk.HIGH or claim_amount >= 5_000
            loop.transition(WorkflowState.APPROVAL if requires_approval else WorkflowState.COMPLETE)
            decision = Decision(
                decision_id=f"decision-{uuid4()}",
                tenant_id=context.actor.tenant_id,
                recommendation="review" if requires_approval else "approve",
                risk=risk,
                status=DecisionStatus.REVIEW_REQUIRED if requires_approval else DecisionStatus.PROPOSED,
                evidence=evidence,
                policy_version="claims-policy-1",
                trace_id=context.correlation_id,
                metadata={"claim_id": claim_id, "claim_amount": claim_amount,
                          "workflow_revision": loop.revision},
            )
            self.audit.append(
                event_type="decision.proposed",
                actor_id=context.actor.actor_id,
                tenant_id=context.actor.tenant_id,
                correlation_id=context.correlation_id,
                details={"decision_id": decision.decision_id, "risk": decision.risk,
                         "status": decision.status, "evidence": [e.document_id for e in evidence]},
            )
            return decision

