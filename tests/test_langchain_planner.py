"""Tests for LangChain planner output parsing."""

import pytest

from gui_agent.agent.planner import _parse_plan_json, _task_plan_from_data


def test_parse_plan_json_accepts_plain_json():
    data = _parse_plan_json('{"steps": [{"tool": "ocr_screen", "description": "observe", "args": {}}]}')

    assert data["steps"][0]["tool"] == "ocr_screen"


def test_parse_plan_json_accepts_markdown_fenced_json():
    data = _parse_plan_json(
        '```json\n{"steps": [{"tool": "type_text", "description": "type", "args": {"text": "hello"}}]}\n```'
    )

    assert data["steps"][0]["args"] == {"text": "hello"}


def test_task_plan_from_data_builds_plan_steps():
    plan = _task_plan_from_data(
        "type hello",
        {"steps": [{"tool": "type_text", "description": "type", "args": {"text": "hello"}}]},
    )

    assert plan.task == "type hello"
    assert plan.steps[0].tool == "type_text"
    assert plan.steps[0].args == {"text": "hello"}


def test_task_plan_from_data_rejects_unknown_tool():
    with pytest.raises(ValueError, match="unsupported tool"):
        _task_plan_from_data("bad", {"steps": [{"tool": "delete_file", "description": "bad", "args": {}}]})

