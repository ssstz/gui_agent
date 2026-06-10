"""Mouse, keyboard, and application control helpers for a basic GUI agent."""

from __future__ import annotations

from dataclasses import dataclass
import logging
import subprocess
import time
from typing import Literal, Sequence
import webbrowser

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


def open_app(command: str, args: Sequence[str] | None = None, *, wait_seconds: float = 0.0) -> ActionResult:
    """Open a desktop application or executable command."""

    try:
        command = command.strip()
        if not command:
            raise ValueError("command must not be empty")

        process_args: str | list[str]
        process_args = [command, *list(args or [])] if args else command
        process = subprocess.Popen(process_args)
        _sleep(wait_seconds)
        return ActionResult("open_app", True, f"opened {command} pid={process.pid}")
    except Exception as exc:
        logger.exception("Open app failed. command=%r args=%r", command, args)
        return ActionResult("open_app", False, f"open app failed: {exc}")


def open_url(url: str, *, wait_seconds: float = 0.0) -> ActionResult:
    """Open a URL with the system default browser."""

    try:
        url = url.strip()
        if not url:
            raise ValueError("url must not be empty")

        opened = webbrowser.open(url)
        _sleep(wait_seconds)
        if not opened:
            return ActionResult("open_url", False, f"browser did not accept url: {url}")
        return ActionResult("open_url", True, f"opened {url}")
    except Exception as exc:
        logger.exception("Open URL failed. url=%r", url)
        return ActionResult("open_url", False, f"open url failed: {exc}")


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


def press_key(key: str, *, presses: int = 1, interval: float = 0.0) -> ActionResult:
    """Press one keyboard key one or more times."""

    try:
        key = key.strip()
        if not key:
            raise ValueError("key must not be empty")
        pyautogui.press(key, presses=presses, interval=interval)
        return ActionResult("press_key", True, f"pressed {key} x{presses}")
    except Exception as exc:
        logger.exception("Press key failed. key=%r presses=%s", key, presses)
        return ActionResult("press_key", False, f"press key failed: {exc}")


def hotkey(keys: Sequence[str] | str, *, interval: float = 0.0) -> ActionResult:
    """Press a keyboard shortcut such as ctrl+a or alt+f4."""

    try:
        normalized_keys = _normalize_keys(keys)
        pyautogui.hotkey(*normalized_keys, interval=interval)
        return ActionResult("hotkey", True, f"pressed {'+'.join(normalized_keys)}")
    except Exception as exc:
        logger.exception("Hotkey failed. keys=%r", keys)
        return ActionResult("hotkey", False, f"hotkey failed: {exc}")


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


def wait(seconds: float) -> ActionResult:
    """Wait for the desktop state to change."""

    try:
        _sleep(seconds)
        return ActionResult("wait", True, f"waited {max(0.0, seconds):.2f}s")
    except Exception as exc:
        logger.exception("Wait failed. seconds=%s", seconds)
        return ActionResult("wait", False, f"wait failed: {exc}")


def _target_center(target: UIElement | tuple[int, int], monitor_index: int | None = None) -> tuple[int, int]:
    if isinstance(target, UIElement):
        return to_global_point(target.center, monitor_index=monitor_index)
    x, y = target
    return to_global_point((int(x), int(y)), monitor_index=monitor_index)


def _normalize_keys(keys: Sequence[str] | str) -> list[str]:
    if isinstance(keys, str):
        normalized = [key.strip() for key in keys.split("+")]
    else:
        normalized = [str(key).strip() for key in keys]
    normalized = [key for key in normalized if key]
    if not normalized:
        raise ValueError("keys must not be empty")
    return normalized


def _sleep(seconds: float) -> None:
    seconds = max(0.0, float(seconds))
    if seconds:
        time.sleep(seconds)
