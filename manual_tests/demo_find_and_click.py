"""Demo: capture the screen, OCR it, find text, and optionally click it."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from gui_agent.desktop_controller import click
from gui_agent.screen_perception import capture_screen, draw_elements, find_text_element, run_ocr


def main() -> int:
    parser = argparse.ArgumentParser(description="Find text on screen and optionally click it.")
    parser.add_argument("keyword", help="Text keyword to locate with OCR.")
    parser.add_argument("--click", action="store_true", help="Actually click the found element.")
    parser.add_argument("--lang", default="ch", help="PaddleOCR language code, default: ch.")
    parser.add_argument("--cpu", action="store_true", help="Disable PaddleOCR GPU inference.")
    parser.add_argument("--delay", type=float, default=3.0, help="Seconds to wait before capture.")
    parser.add_argument("--after-delay", type=float, default=1.0, help="Seconds to wait before after-click capture.")
    parser.add_argument("--monitor-index", type=int, default=None, help="Optional monitor index to capture/click.")
    parser.add_argument("--artifacts-dir", default="artifacts/demo_results", help="Directory for screenshots/results.")
    args = parser.parse_args()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    artifacts_dir = Path(args.artifacts_dir)
    screenshot_path = artifacts_dir / f"{timestamp}_screen.png"
    annotated_path = artifacts_dir / f"{timestamp}_ocr_annotated.png"
    after_path = artifacts_dir / f"{timestamp}_screen_after.png"
    result_path = artifacts_dir / f"{timestamp}_find_and_click.json"

    image = capture_screen(screenshot_path, delay=args.delay, monitor_index=args.monitor_index)
    elements = run_ocr(image, lang=args.lang, use_gpu=not args.cpu)
    target = find_text_element(args.keyword, elements)
    draw_elements(image, elements, annotated_path)

    payload = {
        "keyword": args.keyword,
        "clicked": False,
        "found": target.to_dict() if target else None,
        "element_count": len(elements),
        "screenshot": str(screenshot_path),
        "annotated": str(annotated_path),
        "monitor_index": args.monitor_index,
    }

    if target and args.click:
        action = click(target, monitor_index=args.monitor_index)
        payload["clicked"] = action.ok
        payload["action"] = action.__dict__
        capture_screen(after_path, delay=args.after_delay, monitor_index=args.monitor_index)
        payload["after_screenshot"] = str(after_path)
        payload["after_delay"] = args.after_delay

    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if target else 2


if __name__ == "__main__":
    raise SystemExit(main())
