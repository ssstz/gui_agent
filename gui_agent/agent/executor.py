"""Execute planned GUI-agent tool steps and collect results."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Callable

from .planner import PlanStep, TaskPlan
from .tools import (
    AgentToolState,
    capture_screen_tool,
    click_point_tool,
    click_text_tool,
    drag_tool,
    find_text_tool,
    ocr_screen_tool,
    scroll_tool,
    type_text_tool,
)

ToolFn = Callable[..., dict[str, Any]]


@dataclass(frozen=True)
class StepExecutionResult:
    """Result for one executed plan step."""

    index: int
    tool: str
    description: str
    ok: bool
    output: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PlanExecutionResult:
    """Result for an executed task plan."""

    task: str
    ok: bool
    steps: list[StepExecutionResult]

    def to_dict(self) -> dict[str, Any]:
        return {
            "task": self.task,
            "ok": self.ok,
            "steps": [step.to_dict() for step in self.steps],
        }


class ToolExecutor:
    """Execute TaskPlan steps with GUI agent tools."""

    def __init__(self, state: AgentToolState | None = None, registry: dict[str, ToolFn] | None = None) -> None:
        self.state = state or AgentToolState()
        self.registry = registry or self._default_registry()

    def execute(self, plan: TaskPlan, *, stop_on_error: bool = True) -> PlanExecutionResult:
        results: list[StepExecutionResult] = []
        for index, step in enumerate(plan.steps):
            result = self.execute_step(index, step)
            results.append(result)
            if stop_on_error and not result.ok:
                break
        return PlanExecutionResult(task=plan.task, ok=all(result.ok for result in results), steps=results)

    def execute_step(self, index: int, step: PlanStep) -> StepExecutionResult:
        tool_fn = self.registry.get(step.tool)
        if tool_fn is None:
            output = {"ok": False, "detail": f"unknown tool: {step.tool}"}
            return StepExecutionResult(index, step.tool, step.description, False, output)

        try:
            output = tool_fn(**step.args)
        except Exception as exc:
            output = {"ok": False, "detail": f"tool execution failed: {exc}"}
        ok = bool(output.get("ok", False))
        return StepExecutionResult(index, step.tool, step.description, ok, output)

    def _default_registry(self) -> dict[str, ToolFn]:
        return {
            "capture_screen": lambda **kwargs: capture_screen_tool(self.state, **kwargs),
            "ocr_screen": lambda **kwargs: ocr_screen_tool(self.state, **kwargs),
            "find_text": lambda **kwargs: find_text_tool(self.state, **kwargs),
            "click_text": lambda **kwargs: click_text_tool(self.state, **kwargs),
            "click_point": click_point_tool,
            "type_text": type_text_tool,
            "scroll": scroll_tool,
            "drag": drag_tool,
        }
