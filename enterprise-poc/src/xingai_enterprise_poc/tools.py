from dataclasses import dataclass
from typing import Any, Callable

from .auth import AuthorizationRequest, PolicyEngine
from .audit import AuditLedger
from .models import RequestContext, ToolRequest


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    required_scope: str
    write: bool
    handler: Callable[[dict[str, Any]], dict[str, Any]]


class ToolGateway:
    def __init__(self, tools: list[Tool], policy: PolicyEngine, audit: AuditLedger) -> None:
        self.tools = {tool.name: tool for tool in tools}
        self.policy = policy
        self.audit = audit

    def execute(self, request: ToolRequest, context: RequestContext, approved: bool = False) -> dict[str, Any]:
        context.assert_active()
        tool = self.tools.get(request.name)
        if tool is None:
            raise ValueError("unknown tool")
        self.policy.authorize(
            AuthorizationRequest(context.actor, f"tool.{tool.name}", context.actor.tenant_id, tool.required_scope)
        )
        if tool.write and not approved:
            raise PermissionError("write tool requires explicit approval")
        result = tool.handler(request.arguments)
        self.audit.append(
            event_type="tool.executed",
            actor_id=context.actor.actor_id,
            tenant_id=context.actor.tenant_id,
            correlation_id=context.correlation_id,
            details={"tool": tool.name, "write": tool.write, "approved": approved},
        )
        return result

