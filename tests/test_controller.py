from gui_agent import desktop_controller as dc
from gui_agent.screen_perception import UIElement


def test_click_uses_element_center(monkeypatch):
    calls = []
    monkeypatch.setattr(dc.pyautogui, "moveTo", lambda *args, **kwargs: calls.append(("moveTo", args, kwargs)))
    monkeypatch.setattr(dc.pyautogui, "click", lambda *args, **kwargs: calls.append(("click", args, kwargs)))
    element = UIElement("x", "OK", (10, 20, 40, 20), (30, 30), 0.9)

    result = dc.click(element)

    assert result.ok
    assert calls[0][0] == "moveTo"
    assert calls[0][1][:2] == (30, 30)
    assert calls[1][2]["x"] == 30
    assert calls[1][2]["y"] == 30


def test_click_offsets_coordinates_for_monitor(monkeypatch):
    calls = []
    monkeypatch.setattr(dc, "to_global_point", lambda point, monitor_index=None: (point[0] + 100, point[1] + 200))
    monkeypatch.setattr(dc.pyautogui, "moveTo", lambda *args, **kwargs: calls.append(("moveTo", args, kwargs)))
    monkeypatch.setattr(dc.pyautogui, "click", lambda *args, **kwargs: calls.append(("click", args, kwargs)))

    result = dc.click((10, 20), monitor_index=1)

    assert result.ok
    assert calls[0][1][:2] == (110, 220)
    assert calls[1][2]["x"] == 110
    assert calls[1][2]["y"] == 220


def test_click_returns_failure_result_on_pyautogui_error(monkeypatch, caplog):
    def broken_move(*args, **kwargs):
        raise RuntimeError("mouse unavailable")

    monkeypatch.setattr(dc.pyautogui, "moveTo", broken_move)

    result = dc.click((10, 20))

    assert result.ok is False
    assert "mouse unavailable" in result.detail
    assert "Click failed" in caplog.text


def test_type_text_can_press_enter(monkeypatch):
    calls = []
    monkeypatch.setattr(dc.pyautogui, "write", lambda *args, **kwargs: calls.append(("write", args, kwargs)))
    monkeypatch.setattr(dc.pyautogui, "press", lambda *args, **kwargs: calls.append(("press", args, kwargs)))

    result = dc.type_text("hello", press_enter=True)

    assert result.ok
    assert calls[0][0] == "write"
    assert calls[0][1][0] == "hello"
    assert calls[1][1][0] == "enter"


def test_scroll_moves_to_target_when_present(monkeypatch):
    calls = []
    monkeypatch.setattr(dc.pyautogui, "moveTo", lambda *args, **kwargs: calls.append(("moveTo", args, kwargs)))
    monkeypatch.setattr(dc.pyautogui, "scroll", lambda *args, **kwargs: calls.append(("scroll", args, kwargs)))

    result = dc.scroll(-3, (100, 200))

    assert result.ok
    assert calls[0][0] == "moveTo"
    assert calls[1][1][0] == -3


def test_drag_uses_start_and_end_points(monkeypatch):
    calls = []
    monkeypatch.setattr(dc.pyautogui, "moveTo", lambda *args, **kwargs: calls.append(("moveTo", args, kwargs)))
    monkeypatch.setattr(dc.pyautogui, "dragTo", lambda *args, **kwargs: calls.append(("dragTo", args, kwargs)))

    result = dc.drag((1, 2), (30, 40), duration=0.2)

    assert result.ok
    assert calls[0][1][:2] == (1, 2)
    assert calls[1][1][:2] == (30, 40)
    assert calls[1][2]["duration"] == 0.2
