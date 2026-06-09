"""Manual test: run OCR on a screenshot and save an annotated image."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from gui_agent.screen_perception import capture_screen, draw_elements, run_ocr

EXPECTED_TERMS = [
    "中文 OCR 混合文本测试页面",
    "登录",
    "确认",
    "搜索",
    "设置",
    "提交订单",
    "Cheat Sheet",
    "Settings",
    "Submit",
    "Cancel",
    "123456",
    "2026年1月1日",
    "Version 1.0",
    "订单号",
    "Order-20260101",
    "用户ID",
    "user123",
    "Amount 88.50",
    "已完成",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Manual OCR test.")
    parser.add_argument("--delay", type=float, default=3.0, help="Seconds to wait before capture.")
    parser.add_argument("--cpu", action="store_true", help="Disable PaddleOCR GPU inference.")
    parser.add_argument("--monitor-index", type=int, default=None, help="Optional monitor index to capture.")
    parser.add_argument("--artifacts-dir", default="artifacts/ocr_results")
    args = parser.parse_args()

    output_dir = Path(args.artifacts_dir)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    annotated_path = output_dir / f"{timestamp}_annotated.png"
    result_path = output_dir / f"{timestamp}_ocr.json"

    image = capture_screen(delay=args.delay, monitor_index=args.monitor_index)
    elements = run_ocr(image, lang="ch", use_gpu=not args.cpu)
    draw_elements(image, elements, annotated_path)

    recognized_texts = [element.text for element in elements]
    matched_terms = _match_expected_terms(EXPECTED_TERMS, recognized_texts)
    expected_terms_count = len(EXPECTED_TERMS)
    match_count = len(matched_terms)
    payload = {
        "annotated": str(annotated_path),
        "monitor_index": args.monitor_index,
        "element_count": len(elements),
        "expected_terms": EXPECTED_TERMS,
        "expected_terms_count": expected_terms_count,
        "matched_terms": matched_terms,
        "match_count": match_count,
        "match_rate": match_count / expected_terms_count if expected_terms_count else 0.0,
        "recognized_texts": recognized_texts,
        "elements": [element.to_dict() for element in elements],
    }

    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print("annotated:", annotated_path)
    print("result:", result_path)
    print("elements:", len(elements))
    print("matched:", f"{match_count}/{expected_terms_count}")
    print("match_rate:", payload["match_rate"])
    for element in elements[:10]:
        print(element.to_dict())
    return 0


def _match_expected_terms(expected_terms: list[str], recognized_texts: list[str]) -> list[str]:
    normalized_text = _normalize(" ".join(recognized_texts))
    return [term for term in expected_terms if _normalize(term) in normalized_text]


def _normalize(text: str) -> str:
    return "".join(text.lower().split())


if __name__ == "__main__":
    raise SystemExit(main())
