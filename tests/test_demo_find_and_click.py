import json
import sys

from PIL import Image

from manual_tests import demo_find_and_click as demo
from gui_agent.screen_perception import UIElement


def test_demo_find_and_click_dry_run(monkeypatch, tmp_path):
    image = Image.new("RGB", (100, 50), "white")
    element = UIElement("ocr_0", "Target", (10, 10, 40, 20), (30, 20), 0.99)
    clicked = []

    monkeypatch.setattr(sys, "argv", ["demo_find_and_click.py", "target", "--artifacts-dir", str(tmp_path)])
    monkeypatch.setattr(demo, "capture_screen", lambda save_path, delay=0, monitor_index=None: image)
    monkeypatch.setattr(demo, "run_ocr", lambda image, lang, use_gpu: [element])
    monkeypatch.setattr(demo, "draw_elements", lambda image, elements, save_path: save_path)
    monkeypatch.setattr(demo, "click", lambda target, monitor_index=None: clicked.append(target))

    exit_code = demo.main()

    assert exit_code == 0
    assert clicked == []

    result_files = list(tmp_path.glob("*_find_and_click.json"))
    assert len(result_files) == 1
    payload = json.loads(result_files[0].read_text(encoding="utf-8"))
    assert payload["clicked"] is False
    assert payload["found"]["text"] == "Target"


def test_demo_find_and_click_returns_2_when_not_found(monkeypatch, tmp_path):
    image = Image.new("RGB", (100, 50), "white")

    monkeypatch.setattr(sys, "argv", ["demo_find_and_click.py", "missing", "--artifacts-dir", str(tmp_path)])
    monkeypatch.setattr(demo, "capture_screen", lambda save_path, delay=0, monitor_index=None: image)
    monkeypatch.setattr(demo, "run_ocr", lambda image, lang, use_gpu: [])
    monkeypatch.setattr(demo, "draw_elements", lambda image, elements, save_path: save_path)

    exit_code = demo.main()

    assert exit_code == 2
