"""End-to-end desktop GUI agent integration."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Protocol

from .executor import PlanExecutionResult, ToolExecutor
from .planner import LangChainTaskPlanner, TaskPlan
from .qwen_vl_client import QwenVLChatClient
from .tools import AgentToolState


class TaskPlanner(Protocol):
    def plan(self, task: str) -> TaskPlan:
        ...


@dataclass(frozen=True)
class AgentRunResult:
    """Complete result for one desktop GUI agent run."""

    task: str
    plan: TaskPlan
    execution: PlanExecutionResult

    @property
    def ok(self) -> bool:
        return self.execution.ok

    def to_dict(self) -> dict[str, Any]:
        return {
            "task": self.task,
            "ok": self.ok,
            "plan": self.plan.to_dict(),
            "execution": self.execution.to_dict(),
        }


class DesktopGUIAgent:
    """Connect planner, GUI tools, and executor into one agent entry point."""

    def __init__(
        self,
        planner: TaskPlanner,
        *,
        state: AgentToolState | None = None,
        executor: ToolExecutor | None = None,
    ) -> None:
        self.state = state or AgentToolState()
        self.planner = planner
        self.executor = executor or ToolExecutor(state=self.state)

    def run(self, task: str, *, stop_on_error: bool = True) -> AgentRunResult:
        task = task.strip()
        if not task:
            raise ValueError("task must not be empty")

        plan = self.planner.plan(task)
        execution = self.executor.execute(plan, stop_on_error=stop_on_error)
        return AgentRunResult(task=task, plan=plan, execution=execution)


def create_qwen_desktop_agent(
    *,
    model_name: str = "models/qwen_vl_chat",
    artifacts_dir: str | Path = "artifacts/agent_runs",
    device_map: str = "auto",
    offload_folder: str | Path | None = "models/qwen_offload",
    model_kwargs: dict[str, Any] | None = None,
) -> DesktopGUIAgent:
    """Create a DesktopGUIAgent backed by local Qwen-VL-Chat planning."""

    state = AgentToolState(artifacts_dir=Path(artifacts_dir))
    qwen = QwenVLChatClient(
        model_name=model_name,
        device_map=device_map,
        offload_folder=offload_folder,
        model_kwargs=model_kwargs,
    )
    planner = LangChainTaskPlanner(qwen)
    return DesktopGUIAgent(planner=planner, state=state)


def save_agent_run_result(result: AgentRunResult, path: str | Path) -> Path:
    """Save an AgentRunResult as JSON."""

    import json

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path
