from dataclasses import dataclass
from time import time
from typing import Any, Protocol

from .models import Actor


class SignatureVerifier(Protocol):
    def verify(self, token: str) -> dict[str, Any]:
        """Verify cryptographic signature and return claims."""


@dataclass(frozen=True)
class IdentityConfiguration:
    issuer: str
    audience: str
    clock_skew_seconds: int = 30


class ClaimsVerifier:
    """Validates claims after an approved JOSE library verifies the signature."""

    def __init__(self, signatures: SignatureVerifier, config: IdentityConfiguration) -> None:
        self.signatures = signatures
        self.config = config

    def authenticate(self, token: str) -> Actor:
        claims = self.signatures.verify(token)
        now = time()
        if claims.get("iss") != self.config.issuer:
            raise PermissionError("invalid issuer")
        audience = claims.get("aud", [])
        audiences = {audience} if isinstance(audience, str) else set(audience)
        if self.config.audience not in audiences:
            raise PermissionError("invalid audience")
        if float(claims.get("exp", 0)) + self.config.clock_skew_seconds <= now:
            raise PermissionError("token expired")
        required = ("sub", "tenant_id")
        if any(not claims.get(name) for name in required):
            raise PermissionError("required identity claim missing")
        return Actor(
            str(claims["sub"]),
            str(claims["tenant_id"]),
            frozenset(claims.get("roles", [])),
            frozenset(str(claims.get("scope", "")).split()),
        )

