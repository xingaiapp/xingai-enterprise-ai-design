from dataclasses import dataclass
from typing import Protocol

from .models import RequestContext, ToolRequest
from .observability import Telemetry
from .tools import ToolGateway


class ModelAdapter(Protocol):
    def next_action(self, *, goal: str, observations: tuple[dict, ...]) -> dict: ...


@dataclass(frozen=True)
class HarnessBudget:
    max_steps: int = 5
    max_tool_calls: int = 3


class AgentHarness:
    def __init__(self, model: ModelAdapter, tools: ToolGateway, telemetry: Telemetry) -> None:
        self.model = model
        self.tools = tools
        self.telemetry = telemetry

    def run(self, goal: str, context: RequestContext, budget: HarnessBudget = HarnessBudget()) -> dict:
        observations: list[dict] = []
        tool_calls = 0
        with self.telemetry.trace("agent.run", context.correlation_id):
            for step in range(1, budget.max_steps + 1):
                context.assert_active()
                action = self.model.next_action(goal=goal, observations=tuple(observations))
                if action.get("type") == "final":
                    return {"answer": action["answer"], "steps": step, "observations": observations}
                if action.get("type") != "tool":
                    raise ValueError("model returned unsupported action")
                tool_calls += 1
                if tool_calls > budget.max_tool_calls:
                    raise RuntimeError("tool-call budget exceeded")
                result = self.tools.execute(
                    ToolRequest(action["name"], action.get("arguments", {})), context
                )
                observations.append({"tool": action["name"], "result": result})
        raise RuntimeError("step budget exhausted")

