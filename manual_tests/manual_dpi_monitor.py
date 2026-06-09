"""Manual test: inspect DPI awareness, monitors, and coordinate conversion."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from gui_agent import get_monitors, is_dpi_awareness_enabled
from gui_agent.screen_perception import to_global_point


def main() -> int:
    parser = argparse.ArgumentParser(description="Manual DPI and monitor test.")
    parser.add_argument("--monitor-index", type=int, default=0, help="Monitor index used for coordinate conversion.")
    parser.add_argument("--x", type=int, default=10, help="Local x coordinate.")
    parser.add_argument("--y", type=int, default=20, help="Local y coordinate.")
    parser.add_argument("--artifacts-dir", default="artifacts/dpi_monitor_results")
    args = parser.parse_args()

    monitors = get_monitors()
    local_point = (args.x, args.y)
    global_point = to_global_point(local_point, monitor_index=args.monitor_index)
    payload = {
        "monitor_count": len(monitors),
        "monitors": [monitor.to_dict() for monitor in monitors],
        "dpi_awareness": "enabled" if is_dpi_awareness_enabled() else "disabled",
        "monitor_index": args.monitor_index,
        "local_point": list(local_point),
        "global_point": list(global_point),
    }

    output_dir = Path(args.artifacts_dir)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_path = output_dir / f"{timestamp}_dpi_monitor.json"
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    print("result:", result_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
