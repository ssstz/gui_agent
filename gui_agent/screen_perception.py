"""Screen capture and OCR helpers for a basic GUI agent.

The module keeps heavy OCR dependencies optional at import time so tests and
controller code can run before PaddleOCR models are installed.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from difflib import SequenceMatcher
import ctypes
from ctypes import wintypes
import logging
import os
from pathlib import Path
import re
import site
import sys
import time
import types
from typing import Any, Iterable, Sequence

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import pyautogui

logger = logging.getLogger(__name__)
_DPI_AWARENESS_ENABLED = False


@dataclass(frozen=True)
class MonitorInfo:
    """Physical monitor rectangle in global screen coordinates."""

    index: int
    left: int
    top: int
    width: int
    height: int
    is_primary: bool = False

    @property
    def region(self) -> tuple[int, int, int, int]:
        return (self.left, self.top, self.width, self.height)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class UIElement:
    """Normalized UI element detected from the screen."""

    element_id: str
    text: str
    bbox: tuple[int, int, int, int]
    center: tuple[int, int]
    confidence: float
    element_type: str = "text"
    source: str = "ocr"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def capture_screen(
    save_path: str | Path | None = None,
    region: tuple[int, int, int, int] | None = None,
    delay: float = 0.0,
    monitor_index: int | None = None,
) -> Image.Image:
    """Capture the current screen.

    Args:
        save_path: Optional file path for saving the screenshot.
        region: Optional ``(left, top, width, height)`` capture rectangle.
        delay: Seconds to wait before taking the screenshot.
        monitor_index: Optional monitor index to capture.

    Returns:
        A Pillow RGB image.
    """

    try:
        if delay > 0:
            time.sleep(delay)
        if monitor_index is not None:
            monitor_region = get_monitor(monitor_index).region
            region = monitor_region if region is None else _offset_region(region, monitor_region)
        image = pyautogui.screenshot(region=region).convert("RGB")
        if save_path is not None:
            path = Path(save_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            image.save(path)
        return image
    except Exception as exc:
        logger.exception("Screen capture failed. region=%s monitor_index=%s", region, monitor_index)
        raise RuntimeError(f"screen capture failed: {exc}") from exc


def enable_dpi_awareness() -> None:
    """Make the process use physical pixels on Windows when possible."""

    global _DPI_AWARENESS_ENABLED
    if os.name != "nt":
        _DPI_AWARENESS_ENABLED = False
        return
    try:
        ctypes.windll.user32.SetProcessDPIAware()
        _DPI_AWARENESS_ENABLED = is_dpi_awareness_enabled()
    except Exception as exc:
        logger.warning("Failed to enable Windows DPI awareness: %s", exc)
        _DPI_AWARENESS_ENABLED = is_dpi_awareness_enabled()
        return


def is_dpi_awareness_enabled() -> bool:
    """Return whether the current process is DPI aware on Windows."""

    if os.name != "nt":
        return False
    try:
        return bool(ctypes.windll.user32.IsProcessDPIAware())
    except Exception:
        return _DPI_AWARENESS_ENABLED


def get_monitors() -> list[MonitorInfo]:
    """Return monitor rectangles in global screen coordinates."""

    if os.name == "nt":
        monitors = _get_windows_monitors()
        if monitors:
            return monitors

    try:
        size = pyautogui.size()
        return [MonitorInfo(index=0, left=0, top=0, width=size.width, height=size.height, is_primary=True)]
    except Exception as exc:
        logger.exception("Failed to get monitor size from pyautogui.")
        raise RuntimeError(f"failed to get monitor information: {exc}") from exc


def get_monitor(monitor_index: int) -> MonitorInfo:
    monitors = get_monitors()
    if monitor_index < 0 or monitor_index >= len(monitors):
        raise ValueError(f"monitor_index {monitor_index} is out of range; available: 0-{len(monitors) - 1}")
    return monitors[monitor_index]


def to_global_point(point: tuple[int, int], monitor_index: int | None = None) -> tuple[int, int]:
    """Convert monitor-relative coordinates to global screen coordinates."""

    x, y = int(point[0]), int(point[1])
    if monitor_index is None:
        return x, y
    monitor = get_monitor(monitor_index)
    return monitor.left + x, monitor.top + y


def run_ocr(
    image: Image.Image | np.ndarray | str | Path | None = None,
    *,
    lang: str = "ch",
    use_gpu: bool = True,
    ocr_engine: Any | None = None,
    save_debug_path: str | Path | None = None,
) -> list[UIElement]:
    """Run OCR and return normalized UI elements.

    PaddleOCR is loaded lazily. Pass ``ocr_engine`` in tests to avoid loading
    the real model.
    """

    try:
        input_image = image if image is not None else capture_screen()
        if save_debug_path is not None and isinstance(input_image, Image.Image):
            Path(save_debug_path).parent.mkdir(parents=True, exist_ok=True)
            input_image.save(save_debug_path)

        if ocr_engine is None:
            ocr_engine = create_ocr_engine(lang=lang, use_gpu=use_gpu)

        raw_result = _call_ocr(ocr_engine, _to_ocr_input(input_image))
        return ocr_results_to_elements(raw_result)
    except Exception as exc:
        logger.exception("OCR failed. lang=%s use_gpu=%s", lang, use_gpu)
        return []


def create_ocr_engine(*, lang: str = "ch", use_gpu: bool = True) -> Any:
    """Create a reusable PaddleOCR engine."""

    return _create_paddle_ocr(lang=lang, use_gpu=use_gpu)


def ocr_results_to_elements(raw_result: Any) -> list[UIElement]:
    """Convert PaddleOCR-like output into UIElement objects."""

    lines = list(_iter_ocr_lines(raw_result))
    elements: list[UIElement] = []
    for index, line in enumerate(lines):
        try:
            parsed = _parse_ocr_line(line)
            if parsed is None:
                continue
            points, text, confidence = parsed
            bbox = _points_to_bbox(points)
            center = (bbox[0] + bbox[2] // 2, bbox[1] + bbox[3] // 2)
            elements.append(
                UIElement(
                    element_id=f"ocr_{index}",
                    text=text,
                    bbox=bbox,
                    center=center,
                    confidence=confidence,
                )
            )
        except Exception as exc:
            logger.warning("Skipped invalid OCR line at index %s: %s", index, exc)
    return elements


def find_text_element(
    keyword: str,
    elements: Iterable[UIElement] | None = None,
    *,
    case_sensitive: bool = False,
    min_confidence: float = 0.0,
    fuzzy_threshold: float | None = None,
    return_all: bool = False,
    regex: bool = False,
) -> UIElement | list[UIElement] | None:
    """Find OCR elements matching a keyword.

    Args:
        keyword: Text, fuzzy text, or regex pattern to search.
        elements: OCR elements. If omitted, OCR is run on the current screen.
        case_sensitive: Whether matching should preserve case.
        min_confidence: Minimum OCR confidence required.
        fuzzy_threshold: Optional similarity threshold in [0, 1].
        return_all: Return every match instead of the best match.
        regex: Treat ``keyword`` as a regular expression pattern.
    """

    if not keyword.strip():
        logger.warning("find_text_element received an empty keyword.")
        raise ValueError("keyword must not be empty")
    if fuzzy_threshold is not None and not 0 <= fuzzy_threshold <= 1:
        logger.warning("find_text_element received invalid fuzzy_threshold=%s.", fuzzy_threshold)
        raise ValueError("fuzzy_threshold must be between 0 and 1")

    if elements is None:
        elements = run_ocr()

    matches = []
    for element in elements:
        if element.confidence < min_confidence:
            continue
        try:
            score = _match_score(keyword, element.text, case_sensitive, fuzzy_threshold, regex)
        except re.error as exc:
            logger.warning("Invalid regex pattern %r: %s", keyword, exc)
            return [] if return_all else None
        except Exception as exc:
            logger.warning("Failed to match keyword %r with text %r: %s", keyword, element.text, exc)
            continue
        if score is not None:
            matches.append((element, score))
    if not matches:
        logger.info("No text element matched keyword=%r.", keyword)
        return [] if return_all else None

    matches.sort(key=lambda item: (item[1], item[0].confidence, -len(item[0].text)), reverse=True)
    matched_elements = [element for element, _score in matches]
    return matched_elements if return_all else matched_elements[0]


def _match_score(
    keyword: str,
    text: str,
    case_sensitive: bool,
    fuzzy_threshold: float | None,
    regex: bool,
) -> float | None:
    if regex:
        flags = 0 if case_sensitive else re.IGNORECASE
        return 1.0 if re.search(keyword, text, flags=flags) else None

    needle = keyword if case_sensitive else keyword.lower()
    haystack = text if case_sensitive else text.lower()

    if needle == haystack:
        return 1.0
    if needle in haystack:
        return 0.95

    if fuzzy_threshold is None:
        return None

    normalized_needle = _normalize_for_fuzzy(needle)
    normalized_haystack = _normalize_for_fuzzy(haystack)
    similarity = SequenceMatcher(None, normalized_needle, normalized_haystack).ratio()
    return similarity if similarity >= fuzzy_threshold else None


def _normalize_for_fuzzy(text: str) -> str:
    return re.sub(r"\s+", "", text)


def _offset_region(
    region: tuple[int, int, int, int],
    monitor_region: tuple[int, int, int, int],
) -> tuple[int, int, int, int]:
    left, top, width, height = region
    monitor_left, monitor_top, _monitor_width, _monitor_height = monitor_region
    return (monitor_left + left, monitor_top + top, width, height)


def draw_elements(
    image: Image.Image | np.ndarray,
    elements: Sequence[UIElement],
    save_path: str | Path,
) -> Path:
    """Draw OCR boxes and labels for experiment evidence."""

    canvas = image.convert("RGB") if isinstance(image, Image.Image) else _cv2_to_pil(image)
    draw = ImageDraw.Draw(canvas)
    font = _load_label_font()
    for element in elements:
        x, y, w, h = element.bbox
        draw.rectangle((x, y, x + w, y + h), outline=(255, 180, 0), width=2)
        label = f"{element.text[:24]} {element.confidence:.2f}"
        label_x = x
        label_y = max(y - 24, 0)
        text_bbox = draw.textbbox((label_x, label_y), label, font=font)
        draw.rectangle(text_bbox, fill=(255, 248, 220))
        draw.text((label_x, label_y), label, fill=(20, 20, 20), font=font)
    path = Path(save_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(path)
    return path


def _to_ocr_input(image: Image.Image | np.ndarray | str | Path) -> np.ndarray | str:
    if isinstance(image, (str, Path)):
        return str(image)
    if isinstance(image, Image.Image):
        return _pil_to_cv2(image)
    return image


def _pil_to_cv2(image: Image.Image) -> np.ndarray:
    return cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)


def _cv2_to_pil(image: np.ndarray) -> Image.Image:
    return Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))


def _load_label_font() -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for font_path in _candidate_cjk_fonts():
        if font_path.exists():
            return ImageFont.truetype(str(font_path), size=18)
    return ImageFont.load_default()


def _candidate_cjk_fonts() -> list[Path]:
    windows_fonts = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
    return [
        windows_fonts / "msyh.ttc",
        windows_fonts / "simhei.ttf",
        windows_fonts / "simsun.ttc",
        windows_fonts / "arialuni.ttf",
    ]


def _get_windows_monitors() -> list[MonitorInfo]:
    monitors: list[MonitorInfo] = []

    monitor_enum_proc = ctypes.WINFUNCTYPE(
        wintypes.BOOL,
        wintypes.HMONITOR,
        wintypes.HDC,
        ctypes.POINTER(wintypes.RECT),
        wintypes.LPARAM,
    )

    def callback(_monitor, _hdc, rect, _data):
        current = rect.contents
        left = int(current.left)
        top = int(current.top)
        right = int(current.right)
        bottom = int(current.bottom)
        monitors.append(
            MonitorInfo(
                index=len(monitors),
                left=left,
                top=top,
                width=right - left,
                height=bottom - top,
                is_primary=left == 0 and top == 0,
            )
        )
        return 1

    try:
        ctypes.windll.user32.EnumDisplayMonitors(0, 0, monitor_enum_proc(callback), 0)
    except Exception as exc:
        logger.warning("Windows monitor enumeration failed: %s", exc)
        return []

    return monitors


def _create_paddle_ocr(lang: str, use_gpu: bool) -> Any:
    os.environ.setdefault("PADDLE_PDX_CACHE_HOME", str(Path.cwd() / "artifacts" / "paddlex_cache"))
    _add_nvidia_dll_directories()
    _avoid_modelscope_torch_import()
    try:
        import paddle
        from paddleocr import PaddleOCR
    except ImportError as exc:
        raise RuntimeError(
            "PaddleOCR is not installed in this virtual environment. "
            "Install paddleocr and paddlepaddle, then run again."
        ) from exc

    if use_gpu:
        try:
            paddle.set_device("gpu")
        except Exception as exc:
            logger.warning("Failed to use Paddle GPU, falling back to CPU: %s", exc)
            paddle.set_device("cpu")
    else:
        paddle.set_device("cpu")

    try:
        return PaddleOCR(
            lang=lang,
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=True,
        )
    except TypeError:
        return PaddleOCR(use_angle_cls=True, lang=lang, use_gpu=use_gpu)


def _avoid_modelscope_torch_import() -> None:
    """Avoid PaddleOCR 3.x importing torch through ModelScope on Windows.

    PaddleOCR/PaddleX can download OCR models from HuggingFace, AIStudio, or BOS.
    ModelScope is optional here, but importing it may load torch after paddle and
    trigger CUDA DLL conflicts in a mixed Paddle + PyTorch environment.
    """

    if "modelscope" in sys.modules:
        return

    modelscope_stub = types.ModuleType("modelscope")

    def snapshot_download(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("ModelScope download path is disabled for this OCR demo.")

    modelscope_stub.snapshot_download = snapshot_download  # type: ignore[attr-defined]
    sys.modules["modelscope"] = modelscope_stub


def _add_nvidia_dll_directories() -> None:
    if os.name != "nt" or not hasattr(os, "add_dll_directory"):
        return

    for site_packages in site.getsitepackages():
        torch_lib = Path(site_packages) / "torch" / "lib"
        if torch_lib.exists():
            os.add_dll_directory(str(torch_lib))

        nvidia_root = Path(site_packages) / "nvidia"
        if not nvidia_root.exists():
            continue
        for bin_dir in nvidia_root.glob("*/bin"):
            if bin_dir.exists():
                os.add_dll_directory(str(bin_dir))


def _call_ocr(ocr_engine: Any, image: np.ndarray | str) -> Any:
    try:
        return ocr_engine.ocr(image)
    except TypeError:
        return ocr_engine.ocr(image, cls=True)


def _iter_ocr_lines(raw_result: Any) -> Iterable[Any]:
    if raw_result is None:
        return []
    if isinstance(raw_result, dict):
        return _iter_paddleocr3_lines(raw_result)
    if isinstance(raw_result, list) and raw_result and isinstance(raw_result[0], dict):
        lines: list[Any] = []
        for page in raw_result:
            lines.extend(_iter_paddleocr3_lines(page))
        return lines
    if _looks_like_ocr_line(raw_result):
        return [raw_result]
    if isinstance(raw_result, list) and len(raw_result) == 1 and isinstance(raw_result[0], list):
        return raw_result[0]
    if isinstance(raw_result, list):
        return raw_result
    return []


def _iter_paddleocr3_lines(page_result: dict[str, Any]) -> list[Any]:
    texts = page_result.get("rec_texts") or []
    scores = page_result.get("rec_scores") or []
    polygons = page_result.get("rec_polys")
    if polygons is None:
        polygons = page_result.get("dt_polys")
    if polygons is None:
        polygons = []
    boxes = page_result.get("rec_boxes")
    if boxes is None:
        boxes = []

    lines: list[Any] = []
    for index, text in enumerate(texts):
        points = None
        if index < len(polygons):
            points = _normalize_points(polygons[index])
        elif index < len(boxes):
            points = _box_to_points(boxes[index])

        if points is None:
            continue

        score = float(scores[index]) if index < len(scores) else 0.0
        lines.append([points, (str(text), score)])
    return lines


def _looks_like_ocr_line(value: Any) -> bool:
    return (
        isinstance(value, (list, tuple))
        and len(value) >= 2
        and isinstance(value[1], (list, tuple))
        and len(value[1]) >= 2
        and isinstance(value[1][0], str)
    )


def _parse_ocr_line(line: Any) -> tuple[list[tuple[float, float]], str, float] | None:
    if not _looks_like_ocr_line(line):
        return None
    points = _normalize_points(line[0])
    text = str(line[1][0]).strip()
    confidence = float(line[1][1])
    if not text or not points:
        return None
    return points, text, confidence


def _normalize_points(value: Any) -> list[tuple[float, float]]:
    if hasattr(value, "tolist"):
        value = value.tolist()
    return [(float(x), float(y)) for x, y in value]


def _box_to_points(value: Any) -> list[tuple[float, float]]:
    if hasattr(value, "tolist"):
        value = value.tolist()
    left, top, right, bottom = [float(v) for v in value]
    return [(left, top), (right, top), (right, bottom), (left, bottom)]


def _points_to_bbox(points: Sequence[tuple[float, float]]) -> tuple[int, int, int, int]:
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    left = int(round(min(xs)))
    top = int(round(min(ys)))
    right = int(round(max(xs)))
    bottom = int(round(max(ys)))
    return (left, top, max(right - left, 1), max(bottom - top, 1))


enable_dpi_awareness()
