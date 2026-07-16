from dataclasses import dataclass, field
from enum import StrEnum
from time import time
from typing import Any


class Risk(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class DecisionStatus(StrEnum):
    PROPOSED = "proposed"
    REVIEW_REQUIRED = "review_required"
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass(frozen=True)
class Actor:
    actor_id: str
    tenant_id: str
    roles: frozenset[str]
    scopes: frozenset[str]


@dataclass(frozen=True)
class RequestContext:
    actor: Actor
    correlation_id: str
    deadline_epoch: float

    def assert_active(self) -> None:
        if time() >= self.deadline_epoch:
            raise TimeoutError("request deadline exceeded")


@dataclass(frozen=True)
class Document:
    document_id: str
    tenant_id: str
    text: str
    allowed_roles: frozenset[str]
    version: int = 1


@dataclass(frozen=True)
class Evidence:
    document_id: str
    excerpt: str
    score: float
    version: int


@dataclass(frozen=True)
class ToolRequest:
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class Decision:
    decision_id: str
    tenant_id: str
    recommendation: str
    risk: Risk
    status: DecisionStatus
    evidence: tuple[Evidence, ...]
    policy_version: str
    trace_id: str
    metadata: dict[str, Any] = field(default_factory=dict)

