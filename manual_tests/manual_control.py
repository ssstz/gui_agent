"""Manual tests for mouse and keyboard control actions.

Examples:
    python -m manual_tests.manual_control click --x 100 --y 100
    python -m manual_tests.manual_control type --text hello
    python -m manual_tests.manual_control scroll --amount -3
    python -m manual_tests.manual_control drag --start-x 100 --start-y 100 --end-x 300 --end-y 300
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

import pyautogui

from gui_agent.desktop_controller import click, drag, scroll, type_text
from gui_agent.screen_perception import capture_screen


def main() -> int:
    parser = argparse.ArgumentParser(description="Manual control tests with JSON evidence.")
    parser.add_argument("action", choices=["click", "type", "scroll", "drag"])
    parser.add_argument("--delay", type=float, default=3.0, help="Seconds to wait before action.")
    parser.add_argument("--after-delay", type=float, default=1.0, help="Seconds to wait before after screenshot.")
    parser.add_argument("--x", type=int)
    parser.add_argument("--y", type=int)
    parser.add_argument("--text", default="hello from gui agent")
    parser.add_argument("--amount", type=int, default=-3)
    parser.add_argument("--start-x", type=int)
    parser.add_argument("--start-y", type=int)
    parser.add_argument("--end-x", type=int)
    parser.add_argument("--end-y", type=int)
    parser.add_argument("--monitor-index", type=int, default=None, help="Optional monitor index for coordinates.")
    parser.add_argument("--artifacts-dir", default="artifacts/control_results")
    args = parser.parse_args()

    artifacts_dir = Path(args.artifacts_dir)
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    before_path = artifacts_dir / f"{timestamp}_{args.action}_before.png"
    after_path = artifacts_dir / f"{timestamp}_{args.action}_after.png"
    result_path = artifacts_dir / f"{timestamp}_{args.action}.json"

    before = capture_screen(before_path, delay=args.delay, monitor_index=args.monitor_index)
    before_pos = pyautogui.position()
    screen_size = pyautogui.size()

    if args.action == "click":
        _require(args.x, "--x")
        _require(args.y, "--y")
        params = {"x": args.x, "y": args.y}
        result = click((args.x, args.y), monitor_index=args.monitor_index)
    elif args.action == "type":
        params = {"text": args.text}
        result = type_text(args.text)
    elif args.action == "scroll":
        params = {"amount": args.amount}
        result = scroll(args.amount)
    elif args.action == "drag":
        _require(args.start_x, "--start-x")
        _require(args.start_y, "--start-y")
        _require(args.end_x, "--end-x")
        _require(args.end_y, "--end-y")
        params = {
            "start": [args.start_x, args.start_y],
            "end": [args.end_x, args.end_y],
        }
        result = drag((args.start_x, args.start_y), (args.end_x, args.end_y), monitor_index=args.monitor_index)

    after = capture_screen(after_path, delay=args.after_delay, monitor_index=args.monitor_index)
    after_pos = pyautogui.position()

    payload = {
        "action": args.action,
        "screen_size": [screen_size.width, screen_size.height],
        "mouse_before": [before_pos.x, before_pos.y],
        "mouse_after": [after_pos.x, after_pos.y],
        "before_screenshot": str(before_path),
        "after_screenshot": str(after_path),
        "monitor_index": args.monitor_index,
        "before_image_size": list(before.size),
        "after_image_size": list(after.size),
        "delay": args.delay,
        "after_delay": args.after_delay,
        "result": result.__dict__,
        "params": params,
    }

    result_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def _require(value: int | None, name: str) -> None:
    if value is None:
        raise SystemExit(f"{name} is required for this action")


if __name__ == "__main__":
    raise SystemExit(main())
