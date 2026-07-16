from dataclasses import asdict, dataclass
from hashlib import sha256
from json import dumps
from time import time
from typing import Any


@dataclass(frozen=True)
class AuditEvent:
    event_id: str
    event_type: str
    actor_id: str
    tenant_id: str
    correlation_id: str
    occurred_at: float
    details: dict[str, Any]
    previous_hash: str
    event_hash: str


class AuditLedger:
    """Append-only hash chain for teaching; production uses durable WORM storage."""

    def __init__(self) -> None:
        self._events: list[AuditEvent] = []

    def append(
        self,
        *,
        event_type: str,
        actor_id: str,
        tenant_id: str,
        correlation_id: str,
        details: dict[str, Any],
    ) -> AuditEvent:
        previous_hash = self._events[-1].event_hash if self._events else "GENESIS"
        occurred_at = time()
        body = dumps(
            {
                "event_type": event_type,
                "actor_id": actor_id,
                "tenant_id": tenant_id,
                "correlation_id": correlation_id,
                "occurred_at": occurred_at,
                "details": details,
                "previous_hash": previous_hash,
            },
            sort_keys=True,
        )
        event_hash = sha256(body.encode()).hexdigest()
        event = AuditEvent(
            event_id=f"audit-{len(self._events) + 1}",
            event_type=event_type,
            actor_id=actor_id,
            tenant_id=tenant_id,
            correlation_id=correlation_id,
            occurred_at=occurred_at,
            details=details,
            previous_hash=previous_hash,
            event_hash=event_hash,
        )
        self._events.append(event)
        return event

    def verify(self) -> bool:
        previous = "GENESIS"
        for event in self._events:
            payload = asdict(event)
            claimed_hash = payload.pop("event_hash")
            payload.pop("event_id")
            body = dumps(payload, sort_keys=True)
            if event.previous_hash != previous or sha256(body.encode()).hexdigest() != claimed_hash:
                return False
            previous = claimed_hash
        return True

    @property
    def events(self) -> tuple[AuditEvent, ...]:
        return tuple(self._events)

