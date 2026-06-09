"""Mouse and keyboard control helpers for a basic GUI agent."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Literal

import pyautogui

from .screen_perception import UIElement, to_global_point

MouseButton = Literal["left", "middle", "right"]
logger = logging.getLogger(__name__)

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.05


@dataclass(frozen=True)
class ActionResult:
    action: str
    ok: bool
    detail: str = ""


def click(
    target: UIElement | tuple[int, int],
    *,
    button: MouseButton = "left",
    clicks: int = 1,
    duration: float = 0.1,
    monitor_index: int | None = None,
) -> ActionResult:
    """Move to a target point or UIElement center and click."""

    try:
        x, y = _target_center(target, monitor_index=monitor_index)
        pyautogui.moveTo(x, y, duration=duration)
        pyautogui.click(x=x, y=y, clicks=clicks, button=button)
        return ActionResult("click", True, f"{button} click at ({x}, {y})")
    except Exception as exc:
        logger.exception("Click failed. target=%r monitor_index=%s", target, monitor_index)
        return ActionResult("click", False, f"click failed: {exc}")


def type_text(text: str, *, interval: float = 0.01, press_enter: bool = False) -> ActionResult:
    """Type text into the focused input."""

    try:
        pyautogui.write(text, interval=interval)
        if press_enter:
            pyautogui.press("enter")
        return ActionResult("type", True, f"typed {len(text)} chars")
    except Exception as exc:
        logger.exception("Typing failed.")
        return ActionResult("type", False, f"type failed: {exc}")


def scroll(
    amount: int,
    target: UIElement | tuple[int, int] | None = None,
    *,
    monitor_index: int | None = None,
) -> ActionResult:
    """Scroll vertically. Positive values scroll up, negative values scroll down."""

    try:
        if target is not None:
            x, y = _target_center(target, monitor_index=monitor_index)
            pyautogui.moveTo(x, y, duration=0.05)
        pyautogui.scroll(amount)
        return ActionResult("scroll", True, f"scroll amount {amount}")
    except Exception as exc:
        logger.exception("Scroll failed. amount=%s target=%r monitor_index=%s", amount, target, monitor_index)
        return ActionResult("scroll", False, f"scroll failed: {exc}")


def drag(
    start: UIElement | tuple[int, int],
    end: UIElement | tuple[int, int],
    *,
    duration: float = 0.3,
    button: MouseButton = "left",
    monitor_index: int | None = None,
) -> ActionResult:
    """Drag from one point/UIElement center to another."""

    try:
        start_x, start_y = _target_center(start, monitor_index=monitor_index)
        end_x, end_y = _target_center(end, monitor_index=monitor_index)
        pyautogui.moveTo(start_x, start_y, duration=0.05)
        pyautogui.dragTo(end_x, end_y, duration=duration, button=button)
        return ActionResult("drag", True, f"drag ({start_x}, {start_y}) -> ({end_x}, {end_y})")
    except Exception as exc:
        logger.exception("Drag failed. start=%r end=%r monitor_index=%s", start, end, monitor_index)
        return ActionResult("drag", False, f"drag failed: {exc}")


def _target_center(target: UIElement | tuple[int, int], monitor_index: int | None = None) -> tuple[int, int]:
    if isinstance(target, UIElement):
        return to_global_point(target.center, monitor_index=monitor_index)
    x, y = target
    return to_global_point((int(x), int(y)), monitor_index=monitor_index)
