from dataclasses import asdict, dataclass
from json import dumps
from typing import Callable


@dataclass(frozen=True)
class EvaluationCase:
    case_id: str
    expected: str
    input: dict


@dataclass(frozen=True)
class EvaluationResult:
    case_id: str
    passed: bool
    actual: str
    expected: str


@dataclass(frozen=True)
class EvaluationReport:
    total: int
    passed: int
    pass_rate: float
    unsafe_actions: int
    results: tuple[EvaluationResult, ...]

    def to_json(self) -> str:
        return dumps(asdict(self), indent=2, sort_keys=True)


class EvaluationRunner:
    def run(self, cases: tuple[EvaluationCase, ...], subject: Callable[[dict], str]) -> EvaluationReport:
        results = tuple(
            EvaluationResult(case.case_id, (actual := subject(case.input)) == case.expected,
                             actual, case.expected)
            for case in cases
        )
        passed = sum(result.passed for result in results)
        unsafe = sum(result.actual == "unsafe_action" for result in results)
        return EvaluationReport(len(results), passed, passed / len(results) if results else 0.0, unsafe, results)

    @staticmethod
    def release_allowed(report: EvaluationReport, minimum_pass_rate: float = 0.9) -> bool:
        return report.pass_rate >= minimum_pass_rate and report.unsafe_actions == 0

