from time import time
import unittest

from xingai_enterprise_poc.agents import Risk
from xingai_enterprise_poc.audit import AuditLedger
from xingai_enterprise_poc.auth import AuthorizationRequest, PolicyEngine
from xingai_enterprise_poc.harness import AgentHarness, HarnessBudget
from xingai_enterprise_poc.identity import ClaimsVerifier, IdentityConfiguration
from xingai_enterprise_poc.loops import LoopState, WorkflowState
from xingai_enterprise_poc.mcp import MCPServerAdapter
from xingai_enterprise_poc.models import Actor, Document, RequestContext
from xingai_enterprise_poc.observability import Telemetry
from xingai_enterprise_poc.rag import AuthorizedRetriever
from xingai_enterprise_poc.tools import Tool, ToolGateway
from xingai_enterprise_poc.workflow import ClaimsDecisionWorkflow
from xingai_enterprise_poc.evaluation import EvaluationCase, EvaluationRunner


def context(*, tenant: str = "tenant-a", scopes: frozenset[str] | None = None) -> RequestContext:
    return RequestContext(
        Actor("user-1", tenant, frozenset({"adjuster"}), scopes or frozenset({"knowledge:read"})),
        "trace-1",
        time() + 10,
    )


class TwoStepModel:
    def next_action(self, *, goal: str, observations: tuple[dict, ...]) -> dict:
        if not observations:
            return {"type": "tool", "name": "lookup", "arguments": {"id": goal}}
        return {"type": "final", "answer": observations[0]["result"]["value"]}


class FakeSignatureVerifier:
    def __init__(self, claims: dict) -> None:
        self.claims = claims

    def verify(self, token: str) -> dict:
        if token != "signed-test-token":
            raise PermissionError("signature invalid")
        return self.claims


class ReferencePOCTest(unittest.TestCase):
    def test_identity_checks_audience_and_maps_actor(self) -> None:
        verifier = ClaimsVerifier(
            FakeSignatureVerifier({"iss": "https://id.example", "aud": ["enterprise-poc"],
                                   "exp": time() + 60, "sub": "u-1", "tenant_id": "t-1",
                                   "roles": ["adjuster"], "scope": "knowledge:read"}),
            IdentityConfiguration("https://id.example", "enterprise-poc"),
        )
        actor = verifier.authenticate("signed-test-token")
        self.assertEqual(actor.tenant_id, "t-1")
        self.assertIn("knowledge:read", actor.scopes)

    def test_policy_denies_cross_tenant(self) -> None:
        with self.assertRaisesRegex(PermissionError, "cross-tenant"):
            PolicyEngine().authorize(
                AuthorizationRequest(context().actor, "read", "tenant-b", "knowledge:read")
            )

    def test_retrieval_filters_by_tenant_and_role(self) -> None:
        documents = [
            Document("a", "tenant-a", "claim policy coverage", frozenset({"adjuster"})),
            Document("b", "tenant-b", "claim policy secret", frozenset({"adjuster"})),
            Document("c", "tenant-a", "claim policy legal", frozenset({"legal"})),
        ]
        results = AuthorizedRetriever(documents, PolicyEngine()).retrieve("claim policy", context())
        self.assertEqual([result.document_id for result in results], ["a"])

    def test_audit_chain_detects_no_mutation(self) -> None:
        ledger = AuditLedger()
        ledger.append(event_type="test", actor_id="a", tenant_id="t", correlation_id="c", details={"ok": True})
        self.assertTrue(ledger.verify())

    def test_loop_rejects_illegal_transition(self) -> None:
        state = LoopState()
        with self.assertRaisesRegex(ValueError, "illegal transition"):
            state.transition(WorkflowState.COMPLETE)

    def test_write_tool_requires_approval(self) -> None:
        gateway = ToolGateway(
            [Tool("pay", "Pay claim", "claim:write", True, lambda args: {"paid": args["amount"]})],
            PolicyEngine(), AuditLedger(),
        )
        write_context = context(scopes=frozenset({"claim:write"}))
        with self.assertRaisesRegex(PermissionError, "approval"):
            gateway.execute(
                __import__("xingai_enterprise_poc.models", fromlist=["ToolRequest"]).ToolRequest(
                    "pay", {"amount": 10}
                ),
                write_context,
            )

    def test_harness_runs_bounded_tool_loop(self) -> None:
        gateway = ToolGateway(
            [Tool("lookup", "Read value", "tool:read", False, lambda args: {"value": args["id"]})],
            PolicyEngine(), AuditLedger(),
        )
        result = AgentHarness(TwoStepModel(), gateway, Telemetry()).run(
            "case-7", context(scopes=frozenset({"tool:read"})), HarnessBudget(max_steps=3)
        )
        self.assertEqual(result["answer"], "case-7")
        self.assertEqual(result["steps"], 2)

    def test_mcp_adapter_lists_and_calls_read_tool(self) -> None:
        gateway = ToolGateway(
            [Tool("lookup", "Read value", "tool:read", False, lambda args: {"value": args["id"]})],
            PolicyEngine(), AuditLedger(),
        )
        server = MCPServerAdapter(gateway)
        self.assertEqual(server.list_tools()[0].name, "lookup")
        self.assertEqual(
            server.call_tool("lookup", {"id": "7"}, context(scopes=frozenset({"tool:read"}))),
            {"value": "7"},
        )

    def test_claim_workflow_requires_review_for_high_amount(self) -> None:
        ledger = AuditLedger()
        retriever = AuthorizedRetriever(
            [Document("policy-1", "tenant-a", "claim policy coverage claim-7", frozenset({"adjuster"}))],
            PolicyEngine(),
        )
        decision = ClaimsDecisionWorkflow(retriever, ledger, Telemetry()).propose(
            "claim-7", 12_000, context()
        )
        self.assertEqual(decision.risk, Risk.HIGH)
        self.assertEqual(decision.recommendation, "review")
        self.assertEqual(decision.evidence[0].document_id, "policy-1")
        self.assertTrue(ledger.verify())

    def test_evaluation_runner_blocks_unsafe_action(self) -> None:
        cases = (EvaluationCase("safe", "review", {"risk": "high"}),)
        report = EvaluationRunner().run(cases, lambda _: "unsafe_action")
        self.assertFalse(EvaluationRunner.release_allowed(report))


if __name__ == "__main__":
    unittest.main()
