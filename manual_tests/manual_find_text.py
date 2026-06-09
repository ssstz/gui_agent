"""Manual test: capture the screen, OCR it, and find a text keyword."""

import argparse
import json
from datetime import datetime
from pathlib import Path

from gui_agent.screen_perception import capture_screen, draw_elements, find_text_element, run_ocr


def main() -> int:
    parser = argparse.ArgumentParser(description="Manual text finding test.")
    parser.add_argument("keyword", help="Text to find on the screen.")
    parser.add_argument("--delay", type=float, default=3.0)
    parser.add_argument("--cpu", action="store_true")
    parser.add_argument("--fuzzy-threshold", type=float, default=None)
    parser.add_argument("--return-all", action="store_true")
    parser.add_argument("--regex", action="store_true")
    parser.add_argument("--min-confidence", type=float, default=0.5)
    parser.add_argument("--monitor-index", type=int, default=None, help="Optional monitor index to capture.")
    parser.add_argument("--artifacts-dir", default="artifacts/find_text_results")
    args = parser.parse_args()

    artifacts_dir = Path(args.artifacts_dir)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    screenshot_path = artifacts_dir / f"{timestamp}_screen.png"
    annotated_path = artifacts_dir / f"{timestamp}_annotated.png"
    result_path = artifacts_dir / f"{timestamp}_find_text.json"

    image = capture_screen(screenshot_path, delay=args.delay, monitor_index=args.monitor_index)
    elements = run_ocr(image, use_gpu=not args.cpu)
    draw_elements(image, elements, annotated_path)
    target = find_text_element(
        args.keyword,
        elements,
        min_confidence=args.min_confidence,
        fuzzy_threshold=args.fuzzy_threshold,
        return_all=args.return_all,
        regex=args.regex,
    )
    found_payload = (
        [element.to_dict() for element in target]
        if isinstance(target, list)
        else target.to_dict()
        if target
        else None
    )
    payload = {
        "keyword": args.keyword,
        "found": found_payload,
        "element_count": len(elements),
        "screenshot": str(screenshot_path),
        "annotated": str(annotated_path),
        "monitor_index": args.monitor_index,
        "recognized_texts": [element.text for element in elements],
        "elements": [element.to_dict() for element in elements],
        "match_options": {
            "min_confidence": args.min_confidence,
            "fuzzy_threshold": args.fuzzy_threshold,
            "return_all": args.return_all,
            "regex": args.regex,
        },
    }
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print("elements:", len(elements))
    print("found:", found_payload)
    print("result:", result_path)
    return 0 if target else 2


if __name__ == "__main__":
    raise SystemExit(main())
