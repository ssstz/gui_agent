"""Agent-facing tools built on top of perception and control modules.

The functions in this module return JSON-serializable dictionaries so they can
be used by a planner, LangChain, or manual end-to-end demos.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from gui_agent.desktop_controller import click, drag, scroll, type_text
from gui_agent.screen_perception import (
    UIElement,
    capture_screen,
    draw_elements,
    find_text_element,
    run_ocr,
)


DEFAULT_ARTIFACTS_DIR = Path("artifacts/agent_tools")


@dataclass
class AgentToolState:
    """Small shared state for multi-step GUI agent tool calls."""

    artifacts_dir: Path = DEFAULT_ARTIFACTS_DIR
    last_screenshot_path: Path | None = None
    last_annotated_path: Path | None = None
    last_elements: list[UIElement] = field(default_factory=list)


def capture_screen_tool(
    state: AgentToolState,
    *,
    delay: float = 0.0,
    monitor_index: int | None = None,
) -> dict[str, Any]:
    """Capture the screen and store the screenshot path in tool state."""

    timestamp = _timestamp()
    screenshot_path = state.artifacts_dir / f"{timestamp}_screen.png"
    image = capture_screen(screenshot_path, delay=delay, monitor_index=monitor_index)
    state.last_screenshot_path = screenshot_path
    return {
        "ok": True,
        "screenshot_path": str(screenshot_path),
        "image_size": list(image.size),
        "monitor_index": monitor_index,
    }


def ocr_screen_tool(
    state: AgentToolState,
    *,
    lang: str = "ch",
    use_gpu: bool = True,
    delay: float = 0.0,
    monitor_index: int | None = None,
) -> dict[str, Any]:
    """Capture the screen, run OCR, and cache detected UI elements."""

    timestamp = _timestamp()
    screenshot_path = state.artifacts_dir / f"{timestamp}_screen.png"
    annotated_path = state.artifacts_dir / f"{timestamp}_ocr_annotated.png"
    image = capture_screen(screenshot_path, delay=delay, monitor_index=monitor_index)
    elements = run_ocr(image, lang=lang, use_gpu=use_gpu)
    draw_elements(image, elements, annotated_path)

    state.last_screenshot_path = screenshot_path
    state.last_annotated_path = annotated_path
    state.last_elements = elements
    return {
        "ok": True,
        "screenshot_path": str(screenshot_path),
        "annotated_path": str(annotated_path),
        "element_count": len(elements),
        "elements": [element.to_dict() for element in elements],
    }


def find_text_tool(
    state: AgentToolState,
    keyword: str,
    *,
    min_confidence: float = 0.0,
    fuzzy_threshold: float | None = None,
    return_all: bool = False,
    regex: bool = False,
) -> dict[str, Any]:
    """Find text from cached OCR elements."""

    target = find_text_element(
        keyword,
        state.last_elements,
        min_confidence=min_confidence,
        fuzzy_threshold=fuzzy_threshold,
        return_all=return_all,
        regex=regex,
    )
    if isinstance(target, list):
        found = [element.to_dict() for element in target]
        ok = bool(target)
    else:
        found = target.to_dict() if target else None
        ok = target is not None
    return {
        "ok": ok,
        "keyword": keyword,
        "found": found,
        "return_all": return_all,
    }


def click_text_tool(
    state: AgentToolState,
    keyword: str,
    *,
    monitor_index: int | None = None,
    min_confidence: float = 0.0,
    fuzzy_threshold: float | None = None,
    regex: bool = False,
) -> dict[str, Any]:
    """Find cached OCR text and click its center."""

    target = find_text_element(
        keyword,
        state.last_elements,
        min_confidence=min_confidence,
        fuzzy_threshold=fuzzy_threshold,
        regex=regex,
    )
    if target is None or isinstance(target, list):
        return {"ok": False, "keyword": keyword, "detail": "text element not found"}

    result = click(target, monitor_index=monitor_index)
    return {
        "ok": result.ok,
        "keyword": keyword,
        "target": target.to_dict(),
        "action": result.__dict__,
    }


def click_point_tool(
    x: int,
    y: int,
    *,
    monitor_index: int | None = None,
) -> dict[str, Any]:
    """Click a coordinate point."""

    result = click((x, y), monitor_index=monitor_index)
    return {"ok": result.ok, "action": result.__dict__}


def type_text_tool(text: str, *, press_enter: bool = False) -> dict[str, Any]:
    """Type text into the currently focused UI element."""

    result = type_text(text, press_enter=press_enter)
    return {"ok": result.ok, "action": result.__dict__}


def scroll_tool(amount: int) -> dict[str, Any]:
    """Scroll the active window."""

    result = scroll(amount)
    return {"ok": result.ok, "action": result.__dict__}


def drag_tool(
    start_x: int,
    start_y: int,
    end_x: int,
    end_y: int,
    *,
    monitor_index: int | None = None,
) -> dict[str, Any]:
    """Drag from one coordinate point to another."""

    result = drag((start_x, start_y), (end_x, end_y), monitor_index=monitor_index)
    return {"ok": result.ok, "action": result.__dict__}


def create_langchain_tools(state: AgentToolState) -> list[Any]:
    """Create LangChain StructuredTool objects for the GUI agent tools."""

    try:
        from langchain_core.tools import StructuredTool
    except ImportError as exc:
        raise RuntimeError("langchain-core is required to create LangChain tools") from exc

    def capture_screen_langchain(delay: float = 0.0, monitor_index: int | None = None) -> dict[str, Any]:
        return capture_screen_tool(state, delay=delay, monitor_index=monitor_index)

    def ocr_screen_langchain(
        lang: str = "ch",
        use_gpu: bool = True,
        delay: float = 0.0,
        monitor_index: int | None = None,
    ) -> dict[str, Any]:
        return ocr_screen_tool(state, lang=lang, use_gpu=use_gpu, delay=delay, monitor_index=monitor_index)

    def find_text_langchain(
        keyword: str,
        min_confidence: float = 0.0,
        fuzzy_threshold: float | None = None,
        return_all: bool = False,
        regex: bool = False,
    ) -> dict[str, Any]:
        return find_text_tool(
            state,
            keyword,
            min_confidence=min_confidence,
            fuzzy_threshold=fuzzy_threshold,
            return_all=return_all,
            regex=regex,
        )

    def click_text_langchain(
        keyword: str,
        monitor_index: int | None = None,
        min_confidence: float = 0.0,
        fuzzy_threshold: float | None = None,
        regex: bool = False,
    ) -> dict[str, Any]:
        return click_text_tool(
            state,
            keyword,
            monitor_index=monitor_index,
            min_confidence=min_confidence,
            fuzzy_threshold=fuzzy_threshold,
            regex=regex,
        )

    return [
        StructuredTool.from_function(
            capture_screen_langchain,
            name="capture_screen",
            description="Capture the current desktop screen.",
        ),
        StructuredTool.from_function(
            ocr_screen_langchain,
            name="ocr_screen",
            description="Capture the screen and run OCR.",
        ),
        StructuredTool.from_function(
            find_text_langchain,
            name="find_text",
            description="Find text from the latest OCR result.",
        ),
        StructuredTool.from_function(
            click_text_langchain,
            name="click_text",
            description="Click the latest OCR element matching the given text.",
        ),
        StructuredTool.from_function(click_point_tool, name="click_point", description="Click a screen coordinate."),
        StructuredTool.from_function(type_text_tool, name="type_text", description="Type text into the focused UI element."),
        StructuredTool.from_function(scroll_tool, name="scroll", description="Scroll the active window."),
        StructuredTool.from_function(drag_tool, name="drag", description="Drag from one point to another."),
    ]

def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S_%f")


