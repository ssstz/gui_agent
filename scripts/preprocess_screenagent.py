"""Preprocess ScreenAgent raw data into a compact JSONL format."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


DEFAULT_RAW_DIR = Path("datasets/raw/ScreenAgent")
DEFAULT_OUTPUT_DIR = Path("datasets/processed/ScreenAgent")
SPLITS = ["train", "test"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Preprocess ScreenAgent into JSONL files.")
    parser.add_argument("--raw-dir", default=str(DEFAULT_RAW_DIR))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--splits", nargs="+", default=SPLITS, choices=SPLITS)
    parser.add_argument("--max-records", type=int, default=None, help="Optional limit per split for quick tests.")
    args = parser.parse_args()

    raw_dir = Path(args.raw_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for split in args.splits:
        count = preprocess_split(raw_dir, output_dir, split, args.max_records)
        print(f"{split}: wrote {count} records to {output_dir / (split + '.jsonl')}")
    return 0


def preprocess_split(raw_dir: Path, output_dir: Path, split: str, max_records: int | None) -> int:
    split_dir = raw_dir / split
    output_path = output_dir / f"{split}.jsonl"
    json_files = sorted(split_dir.rglob("*.json")) if split_dir.exists() else []

    count = 0
    with output_path.open("w", encoding="utf-8") as file:
        for json_path in json_files:
            if max_records is not None and count >= max_records:
                break
            sample = _read_json(json_path)
            record = _to_record(sample, json_path, raw_dir, split, count)
            file.write(json.dumps(record, ensure_ascii=False) + "\n")
            count += 1
    return count


def _to_record(sample: dict[str, Any], json_path: Path, raw_dir: Path, split: str, index: int) -> dict[str, Any]:
    session_dir = json_path.parent
    image_name = sample.get("saved_image_name")
    image_path = session_dir / "images" / image_name if image_name else None
    actions = sample.get("actions") if isinstance(sample.get("actions"), list) else []

    session_id = sample.get("session_id") or session_dir.name
    step_id = json_path.stem
    return {
        "id": f"screenagent-{split}-{session_id}-{step_id}",
        "dataset": "ScreenAgent",
        "split": split,
        "task": sample.get("task_prompt") or sample.get("current_task"),
        "task_en": sample.get("task_prompt_en"),
        "task_zh": sample.get("task_prompt_zh"),
        "step_index": index,
        "observation": {
            "image_path": _relative_or_none(image_path),
            "image_exists": bool(image_path and image_path.exists()),
            "width": sample.get("video_width"),
            "height": sample.get("video_height"),
        },
        "action": {
            "action_count": len(actions),
            "actions": [_normalize_action(action) for action in actions],
        },
        "source": {
            "json_path": _relative_or_none(json_path),
            "session_id": session_id,
            "saved_image_name": image_name,
            "status": sample.get("status"),
        },
    }


def _normalize_action(action: Any) -> dict[str, Any]:
    if not isinstance(action, dict):
        return {"raw": action}
    return {
        "type": action.get("action_type") or action.get("type"),
        "element": action.get("element"),
        "value": action.get("value") or action.get("text"),
        "position": action.get("position") or action.get("coordinate"),
        "raw": action,
    }


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _relative_or_none(path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        return str(path.relative_to(Path.cwd()))
    except ValueError:
        return str(path)


if __name__ == "__main__":
    raise SystemExit(main())
