from gui_agent.agent import PlanStep, TaskPlan


def test_plan_step_is_json_serializable_dict():
    step = PlanStep(tool="ocr_screen", description="observe", args={"lang": "ch"})

    assert step.to_dict() == {
        "tool": "ocr_screen",
        "description": "observe",
        "args": {"lang": "ch"},
    }


def test_task_plan_is_json_serializable_dict():
    plan = TaskPlan(
        task="type hello",
        steps=[PlanStep(tool="type_text", description="type", args={"text": "hello"})],
    )

    assert plan.to_dict() == {
        "task": "type hello",
        "steps": [
            {
                "tool": "type_text",
                "description": "type",
                "args": {"text": "hello"},
            }
        ],
    }
