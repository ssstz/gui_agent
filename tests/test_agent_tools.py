from pathlib import Path

from PIL import Image

from gui_agent.agent import tools
from gui_agent.desktop_controller import ActionResult
from gui_agent.screen_perception import UIElement


def test_ocr_screen_tool_updates_state(monkeypatch, tmp_path):
    image = Image.new("RGB", (20, 10), "white")
    element = UIElement("ocr_0", "Settings", (1, 2, 30, 10), (16, 7), 0.99)

    monkeypatch.setattr(tools, "capture_screen", lambda save_path, delay=0.0, monitor_index=None: image)
    monkeypatch.setattr(tools, "run_ocr", lambda image, lang="ch", use_gpu=True: [element])
    monkeypatch.setattr(tools, "draw_elements", lambda image, elements, save_path: Path(save_path))

    state = tools.AgentToolState(artifacts_dir=tmp_path)
    result = tools.ocr_screen_tool(state)

    assert result["ok"] is True
    assert result["element_count"] == 1
    assert state.last_elements == [element]
    assert result["elements"][0]["text"] == "Settings"


def test_find_text_tool_uses_cached_elements():
    state = tools.AgentToolState()
    state.last_elements = [
        UIElement("a", "Cheat Sheet", (0, 0, 100, 20), (50, 10), 0.98),
    ]

    result = tools.find_text_tool(state, "CheatSheet", fuzzy_threshold=0.8)

    assert result["ok"] is True
    assert result["found"]["text"] == "Cheat Sheet"


def test_click_text_tool_clicks_found_element(monkeypatch):
    calls = []
    state = tools.AgentToolState()
    state.last_elements = [
        UIElement("a", "Submit", (0, 0, 100, 20), (50, 10), 0.98),
    ]

    def fake_click(target, monitor_index=None):
        calls.append((target, monitor_index))
        return ActionResult("click", True, "clicked")

    monkeypatch.setattr(tools, "click", fake_click)

    result = tools.click_text_tool(state, "Submit", monitor_index=0)

    assert result["ok"] is True
    assert calls[0][0].text == "Submit"
    assert calls[0][1] == 0


def test_click_text_tool_returns_not_found_when_missing():
    state = tools.AgentToolState()
    state.last_elements = []

    result = tools.click_text_tool(state, "Missing")

    assert result["ok"] is False
    assert "not found" in result["detail"]


def test_control_tools_wrap_action_results(monkeypatch):
    action_result = ActionResult("click", True, "ok")
    monkeypatch.setattr(tools, "click", lambda target, monitor_index=None: action_result)

    result = tools.click_point_tool(10, 20, monitor_index=1)

    assert result["ok"] is True
    assert result["action"]["detail"] == "ok"

