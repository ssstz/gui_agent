from gui_agent.agent.executor import ToolExecutor
from gui_agent.agent.planner import PlanStep, TaskPlan


def test_executor_runs_plan_steps_in_order():
    calls = []

    def first_tool(value):
        calls.append(("first_tool", value))
        return {"ok": True, "value": value}

    def second_tool():
        calls.append(("second_tool", None))
        return {"ok": True}

    plan = TaskPlan(
        task="demo task",
        steps=[
            PlanStep(tool="first_tool", description="first", args={"value": "hello"}),
            PlanStep(tool="second_tool", description="second"),
        ],
    )

    result = ToolExecutor(registry={"first_tool": first_tool, "second_tool": second_tool}).execute(plan)

    assert result.ok is True
    assert calls == [("first_tool", "hello"), ("second_tool", None)]
    assert result.to_dict()["steps"][0]["output"] == {"ok": True, "value": "hello"}


def test_executor_stops_on_failed_step_by_default():
    calls = []

    def failed_tool():
        calls.append("failed_tool")
        return {"ok": False, "detail": "failed"}

    def skipped_tool():
        calls.append("skipped_tool")
        return {"ok": True}

    plan = TaskPlan(
        task="demo task",
        steps=[
            PlanStep(tool="failed_tool", description="fail"),
            PlanStep(tool="skipped_tool", description="skip"),
        ],
    )

    result = ToolExecutor(registry={"failed_tool": failed_tool, "skipped_tool": skipped_tool}).execute(plan)

    assert result.ok is False
    assert calls == ["failed_tool"]
    assert len(result.steps) == 1


def test_executor_can_continue_after_failed_step():
    calls = []

    def failed_tool():
        calls.append("failed_tool")
        return {"ok": False}

    def next_tool():
        calls.append("next_tool")
        return {"ok": True}

    plan = TaskPlan(
        task="demo task",
        steps=[
            PlanStep(tool="failed_tool", description="fail"),
            PlanStep(tool="next_tool", description="next"),
        ],
    )

    result = ToolExecutor(registry={"failed_tool": failed_tool, "next_tool": next_tool}).execute(
        plan,
        stop_on_error=False,
    )

    assert result.ok is False
    assert calls == ["failed_tool", "next_tool"]
    assert len(result.steps) == 2


def test_executor_reports_unknown_tool():
    plan = TaskPlan(task="demo task", steps=[PlanStep(tool="missing_tool", description="missing")])

    result = ToolExecutor(registry={}).execute(plan)

    assert result.ok is False
    assert result.steps[0].output == {"ok": False, "detail": "unknown tool: missing_tool"}


def test_executor_catches_tool_exception():
    def broken_tool():
        raise RuntimeError("boom")

    plan = TaskPlan(task="demo task", steps=[PlanStep(tool="broken_tool", description="broken")])

    result = ToolExecutor(registry={"broken_tool": broken_tool}).execute(plan)

    assert result.ok is False
    assert result.steps[0].output["ok"] is False
    assert "boom" in result.steps[0].output["detail"]
