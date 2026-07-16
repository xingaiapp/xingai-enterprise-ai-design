from dataclasses import dataclass

from .models import Actor


@dataclass(frozen=True)
class AuthorizationRequest:
    actor: Actor
    action: str
    resource_tenant_id: str
    required_scope: str
    allowed_roles: frozenset[str] = frozenset()


class PolicyEngine:
    """Small deny-by-default RBAC + ABAC reference policy."""

    version = "policy-2026-07"

    def authorize(self, request: AuthorizationRequest) -> None:
        if request.actor.tenant_id != request.resource_tenant_id:
            raise PermissionError("cross-tenant access denied")
        if request.required_scope not in request.actor.scopes:
            raise PermissionError("required scope missing")
        if request.allowed_roles and request.actor.roles.isdisjoint(request.allowed_roles):
            raise PermissionError("role not authorized")

