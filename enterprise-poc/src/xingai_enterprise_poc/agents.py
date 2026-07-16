from dataclasses import dataclass

from .models import Evidence, Risk


@dataclass(frozen=True)
class SpecialistResult:
    specialist: str
    finding: str
    risk: Risk
    evidence_ids: tuple[str, ...]


class PolicySpecialist:
    def review(self, evidence: tuple[Evidence, ...]) -> SpecialistResult:
        insufficient = not evidence
        return SpecialistResult(
            "policy",
            "insufficient policy evidence" if insufficient else "policy evidence located",
            Risk.HIGH if insufficient else Risk.LOW,
            tuple(item.document_id for item in evidence),
        )


class FraudSpecialist:
    def review(self, claim_amount: float, evidence: tuple[Evidence, ...]) -> SpecialistResult:
        high = claim_amount >= 10_000
        return SpecialistResult(
            "fraud",
            "enhanced review required" if high else "standard review",
            Risk.HIGH if high else Risk.LOW,
            tuple(item.document_id for item in evidence),
        )


def consensus(results: tuple[SpecialistResult, ...]) -> Risk:
    return max((result.risk for result in results), default=Risk.MEDIUM, key=list(Risk).index)

