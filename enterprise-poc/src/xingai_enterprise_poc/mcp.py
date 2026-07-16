from dataclasses import dataclass
from typing import Any

from .models import RequestContext, ToolRequest
from .tools import ToolGateway


@dataclass(frozen=True)
class MCPToolDefinition:
    name: str
    description: str
    input_schema: dict[str, Any]


class MCPServerAdapter:
    """Protocol-shaped adapter; wire to an official MCP SDK for remote transport."""

    def __init__(self, gateway: ToolGateway) -> None:
        self.gateway = gateway

    def list_tools(self) -> tuple[MCPToolDefinition, ...]:
        return tuple(
            MCPToolDefinition(
                tool.name,
                tool.description,
                {"type": "object", "additionalProperties": False},
            )
            for tool in self.gateway.tools.values()
        )

    def call_tool(self, name: str, arguments: dict, context: RequestContext) -> dict:
        return self.gateway.execute(ToolRequest(name, arguments), context)

