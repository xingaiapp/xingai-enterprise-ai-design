from collections import Counter
from contextlib import contextmanager
from dataclasses import dataclass
from logging import Logger, getLogger
from time import perf_counter
from typing import Iterator


@dataclass(frozen=True)
class Span:
    name: str
    correlation_id: str
    duration_ms: float
    success: bool


class Telemetry:
    def __init__(self, logger: Logger | None = None) -> None:
        self.logger = logger or getLogger("xingai.enterprise")
        self.metrics: Counter[str] = Counter()
        self.spans: list[Span] = []

    @contextmanager
    def trace(self, name: str, correlation_id: str) -> Iterator[None]:
        started = perf_counter()
        success = False
        try:
            yield
            success = True
            self.metrics[f"{name}.success"] += 1
        except Exception:
            self.metrics[f"{name}.failure"] += 1
            raise
        finally:
            span = Span(name, correlation_id, (perf_counter() - started) * 1000, success)
            self.spans.append(span)
            self.logger.info(
                "operation_finished",
                extra={"operation": name, "correlation_id": correlation_id,
                       "duration_ms": span.duration_ms, "success": success},
            )

