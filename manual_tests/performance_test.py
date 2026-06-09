"""Manual performance test for the screen -> OCR -> find-text -> click pipeline."""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Any

from gui_agent.desktop_controller import click
from gui_agent.screen_perception import capture_screen, create_ocr_engine, find_text_element, run_ocr


def main() -> int:
    parser = argparse.ArgumentParser(description="Measure capture, OCR, text finding, and click performance.")
    parser.add_argument("keyword", help="Text to find during the performance test.")
    parser.add_argument("--runs", type=int, default=10, help="Number of measured runs.")
    parser.add_argument("--start-delay", type=float, default=3.0, help="Seconds to wait before the first run.")
    parser.add_argument("--interval", type=float, default=0.2, help="Seconds to wait between runs.")
    parser.add_argument("--cpu", action="store_true", help="Disable PaddleOCR GPU inference.")
    parser.add_argument("--lang", default="ch", help="PaddleOCR language code, default: ch.")
    parser.add_argument("--fuzzy-threshold", type=float, default=None)
    parser.add_argument("--regex", action="store_true")
    parser.add_argument("--min-confidence", type=float, default=0.5)
    parser.add_argument("--monitor-index", type=int, default=None, help="Optional monitor index to capture.")
    parser.add_argument("--artifacts-dir", default="artifacts/performance_results")
    args = parser.parse_args()

    if args.runs <= 0:
        raise SystemExit("--runs must be greater than 0")

    output_dir = Path(args.artifacts_dir)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_path = output_dir / f"{timestamp}_performance.json"

    print(f"Waiting {args.start_delay} seconds before performance test...")
    if args.start_delay > 0:
        time.sleep(args.start_delay)

    model_load_start = time.perf_counter()
    ocr_engine = create_ocr_engine(lang=args.lang, use_gpu=not args.cpu)
    model_load_seconds = time.perf_counter() - model_load_start

    runs: list[dict[str, Any]] = []
    for index in range(args.runs):
        total_start = time.perf_counter()

        capture_start = time.perf_counter()
        image = capture_screen(monitor_index=args.monitor_index)
        capture_seconds = time.perf_counter() - capture_start

        ocr_start = time.perf_counter()
        elements = run_ocr(image, lang=args.lang, use_gpu=not args.cpu, ocr_engine=ocr_engine)
        ocr_seconds = time.perf_counter() - ocr_start

        find_start = time.perf_counter()
        found = find_text_element(
            args.keyword,
            elements,
            min_confidence=args.min_confidence,
            fuzzy_threshold=args.fuzzy_threshold,
            regex=args.regex,
        )
        find_seconds = time.perf_counter() - find_start

        click_seconds = 0.0
        clicked = False
        click_result = None
        if found:
            click_start = time.perf_counter()
            action = click(found, monitor_index=args.monitor_index)
            click_seconds = time.perf_counter() - click_start
            clicked = action.ok
            click_result = action.__dict__

        total_seconds = time.perf_counter() - total_start
        run_payload = {
            "run": index + 1,
            "capture_seconds": capture_seconds,
            "ocr_seconds": ocr_seconds,
            "find_seconds": find_seconds,
            "click_seconds": click_seconds,
            "total_seconds": total_seconds,
            "element_count": len(elements),
            "found": found.to_dict() if found else None,
            "clicked": clicked,
            "click_result": click_result,
        }
        runs.append(run_payload)

        print(
            f"run {index + 1}/{args.runs}: "
            f"total={total_seconds:.3f}s, "
            f"capture={capture_seconds:.3f}s, "
            f"ocr={ocr_seconds:.3f}s, "
            f"find={find_seconds:.3f}s, "
            f"click={click_seconds:.3f}s, "
            f"elements={len(elements)}, "
            f"found={bool(found)}, "
            f"clicked={clicked}"
        )
        if args.interval > 0 and index < args.runs - 1:
            time.sleep(args.interval)

    averages = {
        "capture_seconds": mean(run["capture_seconds"] for run in runs),
        "ocr_seconds": mean(run["ocr_seconds"] for run in runs),
        "find_seconds": mean(run["find_seconds"] for run in runs),
        "click_seconds": mean(run["click_seconds"] for run in runs),
        "total_seconds": mean(run["total_seconds"] for run in runs),
        "element_count": mean(run["element_count"] for run in runs),
    }
    measured_steps = ["capture_seconds", "ocr_seconds", "find_seconds", "click_seconds"]
    bottleneck = max(measured_steps, key=lambda key: averages[key])
    payload = {
        "keyword": args.keyword,
        "runs_count": args.runs,
        "lang": args.lang,
        "use_gpu": not args.cpu,
        "click_enabled": True,
        "monitor_index": args.monitor_index,
        "model_load_seconds": model_load_seconds,
        "averages": averages,
        "bottleneck": bottleneck,
        "match_options": {
            "min_confidence": args.min_confidence,
            "fuzzy_threshold": args.fuzzy_threshold,
            "regex": args.regex,
        },
        "runs": runs,
    }

    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print("result:", result_path)
    print("model_load_seconds:", f"{model_load_seconds:.3f}")
    print("average_total_seconds:", f"{averages['total_seconds']:.3f}")
    print("bottleneck:", bottleneck)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
