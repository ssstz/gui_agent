import json

import pytest

from gui_agent.agent import DesktopGUIAgent, PlanStep, TaskPlan, ToolExecutor, save_agent_run_result


class FakePlanner:
    def __init__(self, plan):
        self.plan_value = plan
        self.tasks = []

    def plan(self, task):
        self.tasks.append(task)
        return self.plan_value


def test_desktop_gui_agent_runs_planner_and_executor():
    calls = []
    plan = TaskPlan(
        task="demo task",
        steps=[
            PlanStep(tool="ocr_screen", description="observe"),
            PlanStep(tool="type_text", description="type", args={"text": "hello"}),
        ],
    )
    planner = FakePlanner(plan)
    executor = ToolExecutor(
        registry={
            "ocr_screen": lambda: {"ok": True, "element_count": 1},
            "type_text": lambda text: calls.append(text) or {"ok": True},
        }
    )

    result = DesktopGUIAgent(planner=planner, executor=executor).run(" demo task ")

    assert result.ok is True
    assert planner.tasks == ["demo task"]
    assert calls == ["hello"]
    assert result.to_dict()["plan"]["steps"][0]["tool"] == "ocr_screen"
    assert result.to_dict()["execution"]["steps"][1]["ok"] is True


def test_desktop_gui_agent_rejects_empty_task():
    planner = FakePlanner(TaskPlan(task="unused", steps=[]))

    with pytest.raises(ValueError):
        DesktopGUIAgent(planner=planner).run("   ")


def test_save_agent_run_result_writes_json(tmp_path):
    plan = TaskPlan(task="demo task", steps=[PlanStep(tool="ocr_screen", description="observe")])
    executor = ToolExecutor(registry={"ocr_screen": lambda: {"ok": True}})
    result = DesktopGUIAgent(planner=FakePlanner(plan), executor=executor).run("demo task")

    output_path = save_agent_run_result(result, tmp_path / "result.json")

    data = json.loads(output_path.read_text(encoding="utf-8"))
    assert data["task"] == "demo task"
    assert data["ok"] is True
    assert data["execution"]["steps"][0]["tool"] == "ocr_screen"
