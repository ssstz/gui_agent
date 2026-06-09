"""Basic desktop perception and control package for GUI agent demos."""

from .desktop_controller import ActionResult, click, drag, scroll, type_text
from .screen_perception import (
    MonitorInfo,
    UIElement,
    capture_screen,
    create_ocr_engine,
    find_text_element,
    get_monitor,
    get_monitors,
    is_dpi_awareness_enabled,
    run_ocr,
)

__all__ = [
    "ActionResult",
    "MonitorInfo",
    "UIElement",
    "capture_screen",
    "click",
    "create_ocr_engine",
    "drag",
    "find_text_element",
    "get_monitor",
    "get_monitors",
    "is_dpi_awareness_enabled",
    "run_ocr",
    "scroll",
    "type_text",
]
