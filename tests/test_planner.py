import pytest

from gui_agent.agent import SimpleTaskPlanner


def test_planner_creates_search_plan():
    planner = SimpleTaskPlanner()

    plan = planner.plan("search von Neumann")

    assert plan.task == "search von Neumann"
    assert [step.tool for step in plan.steps] == ["ocr_screen", "click_text", "type_text", "ocr_screen"]
    assert plan.steps[1].args["keyword"] == "search"
    assert plan.steps[2].args == {"text": "von Neumann", "press_enter": True}


def test_planner_extracts_quoted_text_for_typing():
    planner = SimpleTaskPlanner()

    plan = planner.plan('write "hello gui agent"')

    type_steps = [step for step in plan.steps if step.tool == "type_text"]
    assert type_steps[0].args == {"text": "hello gui agent", "press_enter": False}


def test_planner_creates_click_plan():
    planner = SimpleTaskPlanner()

    plan = planner.plan("click Settings")

    assert plan.steps[1].tool == "click_text"
    assert plan.steps[1].args["keyword"] == "Settings"
    assert plan.steps[1].args["fuzzy_threshold"] == 0.8


def test_planner_creates_scroll_plan():
    planner = SimpleTaskPlanner()

    plan = planner.plan("scroll down")

    scroll_steps = [step for step in plan.steps if step.tool == "scroll"]
    assert scroll_steps[0].args == {"amount": -500}


def test_plan_is_json_serializable_dict():
    planner = SimpleTaskPlanner()

    payload = planner.plan("搜索 冯诺依曼").to_dict()

    assert payload["task"] == "搜索 冯诺依曼"
    assert payload["steps"][0]["tool"] == "ocr_screen"
    assert payload["steps"][2]["args"] == {"text": "冯诺依曼", "press_enter": True}


def test_planner_rejects_empty_task():
    planner = SimpleTaskPlanner()

    with pytest.raises(ValueError):
        planner.plan("   ")
