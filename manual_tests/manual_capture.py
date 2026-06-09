"""Manual test: capture the current screen after a short delay."""

import argparse
from datetime import datetime
from pathlib import Path

from gui_agent.screen_perception import capture_screen


def main() -> None:
    parser = argparse.ArgumentParser(description="Manual screen capture test.")
    parser.add_argument("--delay", type=float, default=3.0, help="Seconds to wait before capture.")
    parser.add_argument("--monitor-index", type=int, default=None, help="Optional monitor index to capture.")
    parser.add_argument("--artifacts-dir", default="artifacts/capture_results")
    args = parser.parse_args()

    output_dir = Path(args.artifacts_dir)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    screenshot_path = output_dir / f"{timestamp}_screen.png"

    image = capture_screen(screenshot_path, delay=args.delay, monitor_index=args.monitor_index)
    print("saved:", screenshot_path)
    print("size:", image.size)
    print("mode:", image.mode)


if __name__ == "__main__":
    main()
