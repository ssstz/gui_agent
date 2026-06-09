from PIL import Image

from gui_agent import screen_perception as sp


def test_capture_screen_returns_and_saves_image(monkeypatch, tmp_path):
    expected = Image.new("RGB", (20, 10), "white")
    monkeypatch.setattr(sp.pyautogui, "screenshot", lambda region=None: expected)

    output = tmp_path / "screen.png"
    image = sp.capture_screen(output)

    assert image.size == (20, 10)
    assert image.mode == "RGB"
    assert output.exists()


def test_capture_screen_can_use_monitor_region(monkeypatch):
    expected = Image.new("RGB", (30, 40), "white")
    calls = []
    monitor = sp.MonitorInfo(index=1, left=100, top=200, width=30, height=40)

    monkeypatch.setattr(sp, "get_monitor", lambda monitor_index: monitor)
    monkeypatch.setattr(sp.pyautogui, "screenshot", lambda region=None: calls.append(region) or expected)

    image = sp.capture_screen(monitor_index=1)

    assert image.size == (30, 40)
    assert calls == [(100, 200, 30, 40)]


def test_capture_screen_offsets_region_inside_monitor(monkeypatch):
    expected = Image.new("RGB", (5, 6), "white")
    calls = []
    monitor = sp.MonitorInfo(index=1, left=100, top=200, width=300, height=400)

    monkeypatch.setattr(sp, "get_monitor", lambda monitor_index: monitor)
    monkeypatch.setattr(sp.pyautogui, "screenshot", lambda region=None: calls.append(region) or expected)

    sp.capture_screen(region=(10, 20, 5, 6), monitor_index=1)

    assert calls == [(110, 220, 5, 6)]


def test_to_global_point_offsets_local_point_by_monitor(monkeypatch):
    monitor = sp.MonitorInfo(index=1, left=100, top=200, width=300, height=400)
    monkeypatch.setattr(sp, "get_monitor", lambda monitor_index: monitor)

    point = sp.to_global_point((10, 20), monitor_index=1)

    assert point == (110, 220)


def test_run_ocr_with_fake_engine():
    class FakeOCR:
        def ocr(self, image, cls=True):
            return [[[[[1, 2], [11, 2], [11, 12], [1, 12]], ("OK", 0.99)]]]

    elements = sp.run_ocr(Image.new("RGB", (12, 12)), ocr_engine=FakeOCR())

    assert len(elements) == 1
    assert elements[0].text == "OK"
    assert elements[0].bbox == (1, 2, 10, 10)
    assert elements[0].center == (6, 7)


def test_run_ocr_returns_empty_list_when_engine_fails(caplog):
    class BrokenOCR:
        def ocr(self, image):
            raise RuntimeError("ocr unavailable")

    elements = sp.run_ocr(Image.new("RGB", (12, 12)), ocr_engine=BrokenOCR())

    assert elements == []
    assert "OCR failed" in caplog.text


def test_ocr_results_to_elements_converts_raw_result():
    raw = [
        {
            "rec_texts": ["File", "Confirm"],
            "rec_scores": [0.99, 0.88],
            "rec_polys": [
                [[1, 2], [41, 2], [41, 22], [1, 22]],
                [[50, 60], [90, 60], [90, 80], [50, 80]],
            ],
        }
    ]

    elements = sp.ocr_results_to_elements(raw)

    assert len(elements) == 2
    assert elements[0].text == "File"
    assert elements[0].bbox == (1, 2, 40, 20)
    assert elements[0].center == (21, 12)
    assert elements[1].text == "Confirm"
    assert elements[1].confidence == 0.88


def test_find_text_element_locates_keyword():
    elements = [
        sp.UIElement("a", "Settings", (0, 0, 80, 20), (40, 10), 0.92),
        sp.UIElement("b", "Open File", (100, 0, 90, 20), (145, 10), 0.95),
    ]

    found = sp.find_text_element("file", elements)

    assert found is not None
    assert found.element_id == "b"
    assert found.center == (145, 10)


def test_find_text_element_returns_none_when_missing():
    elements = [
        sp.UIElement("a", "Settings", (0, 0, 80, 20), (40, 10), 0.92),
    ]

    found = sp.find_text_element("File", elements)

    assert found is None


def test_find_text_element_supports_fuzzy_matching():
    elements = [
        sp.UIElement("a", "Cheat Sheet", (0, 0, 100, 20), (50, 10), 0.98),
    ]

    found = sp.find_text_element("CheatSheet", elements, fuzzy_threshold=0.8)

    assert found is not None
    assert found.element_id == "a"


def test_find_text_element_rejects_low_fuzzy_similarity():
    elements = [
        sp.UIElement("a", "Cheat Sheet", (0, 0, 100, 20), (50, 10), 0.98),
    ]

    found = sp.find_text_element("Christmas", elements, fuzzy_threshold=0.9)

    assert found is None


def test_find_text_element_can_return_all_matches():
    elements = [
        sp.UIElement("a", "Settings", (0, 0, 80, 20), (40, 10), 0.92),
        sp.UIElement("b", "Advanced Settings", (100, 0, 160, 20), (180, 10), 0.96),
        sp.UIElement("c", "Submit", (0, 40, 80, 20), (40, 50), 0.99),
    ]

    found = sp.find_text_element("Settings", elements, return_all=True)

    assert isinstance(found, list)
    assert [element.element_id for element in found] == ["a", "b"]


def test_find_text_element_supports_regex_matching():
    elements = [
        sp.UIElement("a", "Version 1.0", (0, 0, 100, 20), (50, 10), 0.94),
        sp.UIElement("b", "Build alpha", (0, 30, 100, 20), (50, 40), 0.95),
    ]

    found = sp.find_text_element(r"Version\s+\d+\.\d+", elements, regex=True)

    assert found is not None
    assert found.element_id == "a"


def test_find_text_element_validates_fuzzy_threshold():
    elements = [
        sp.UIElement("a", "Settings", (0, 0, 80, 20), (40, 10), 0.92),
    ]

    try:
        sp.find_text_element("Settings", elements, fuzzy_threshold=1.5)
    except ValueError as exc:
        assert "fuzzy_threshold" in str(exc)
    else:
        raise AssertionError("invalid fuzzy_threshold should raise ValueError")


def test_find_text_element_returns_none_for_invalid_regex(caplog):
    elements = [
        sp.UIElement("a", "Settings", (0, 0, 80, 20), (40, 10), 0.92),
    ]

    found = sp.find_text_element("[", elements, regex=True)

    assert found is None
    assert "Invalid regex pattern" in caplog.text
