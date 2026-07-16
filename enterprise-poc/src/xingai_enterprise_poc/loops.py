from dataclasses import dataclass
from enum import StrEnum


class WorkflowState(StrEnum):
    INTAKE = "intake"
    RESEARCH = "research"
    REVIEW = "review"
    APPROVAL = "approval"
    COMPLETE = "complete"
    REJECTED = "rejected"


ALLOWED: dict[WorkflowState, frozenset[WorkflowState]] = {
    WorkflowState.INTAKE: frozenset({WorkflowState.RESEARCH}),
    WorkflowState.RESEARCH: frozenset({WorkflowState.REVIEW}),
    WorkflowState.REVIEW: frozenset({WorkflowState.APPROVAL, WorkflowState.COMPLETE}),
    WorkflowState.APPROVAL: frozenset({WorkflowState.COMPLETE, WorkflowState.REJECTED}),
}


@dataclass
class LoopState:
    state: WorkflowState = WorkflowState.INTAKE
    revision: int = 0

    def transition(self, target: WorkflowState) -> None:
        if target not in ALLOWED.get(self.state, frozenset()):
            raise ValueError(f"illegal transition: {self.state} -> {target}")
        self.state = target
        self.revision += 1

