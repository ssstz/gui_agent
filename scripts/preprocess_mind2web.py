"""Preprocess Multimodal-Mind2Web into compact split JSONL files."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any


DATASET_NAME = "osunlp/Multimodal-Mind2Web"
DEFAULT_RAW_DIR = Path("datasets/raw/Mind2Web")
DEFAULT_OUTPUT_DIR = Path("datasets/processed/Mind2Web")
SPLITS = ["train", "test_task", "test_website", "test_domain"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Preprocess Multimodal-Mind2Web into JSONL files.")
    parser.add_argument("--raw-dir", default=str(DEFAULT_RAW_DIR))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--splits", nargs="+", default=SPLITS, choices=SPLITS)
    parser.add_argument("--max-records", type=int, default=None, help="Optional limit per split for quick tests.")
    parser.add_argument("--save-images", action="store_true", help="Save screenshots to processed image folders.")
    args = parser.parse_args()

    raw_dir = Path(args.raw_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    cache_root = raw_dir / "huggingface_cache"
    tmp_dir = raw_dir / "tmp"
    _set_hf_cache_env(cache_root, tmp_dir)

    from datasets import load_dataset

    for split in args.splits:
        dataset = load_dataset(
            DATASET_NAME,
            split=split,
            cache_dir=str((cache_root / "datasets").resolve()),
        )
        count = preprocess_split(dataset, output_dir, split, args.max_records, args.save_images)
        print(f"{split}: wrote {count} records to {output_dir / (split + '.jsonl')}")
    return 0


def preprocess_split(dataset: Any, output_dir: Path, split: str, max_records: int | None, save_images: bool) -> int:
    output_path = output_dir / f"{split}.jsonl"
    image_dir = output_dir / "images" / split
    if save_images:
        image_dir.mkdir(parents=True, exist_ok=True)

    count = 0
    with output_path.open("w", encoding="utf-8") as file:
        for index, sample in enumerate(dataset):
            if max_records is not None and count >= max_records:
                break
            image_path = _save_image(sample, image_dir, split, index) if save_images else None
            record = _to_record(sample, split, index, image_path)
            file.write(json.dumps(record, ensure_ascii=False) + "\n")
            count += 1
    return count


def _to_record(sample: dict[str, Any], split: str, index: int, image_path: Path | None) -> dict[str, Any]:
    operation = _as_dict(sample.get("operation"))
    pos_candidates = sample.get("pos_candidates") or []
    neg_candidates = sample.get("neg_candidates") or []
    screenshot = sample.get("screenshot")
    action_uid = sample.get("action_uid") or f"row-{index}"

    return {
        "id": f"mind2web-{split}-{action_uid}",
        "dataset": "Multimodal-Mind2Web",
        "split": split,
        "task": sample.get("confirmed_task"),
        "step_index": _to_int_or_none(sample.get("target_action_index")),
        "observation": {
            "image_path": _relative_or_none(image_path),
            "has_screenshot": screenshot is not None,
            "screenshot_size": list(getattr(screenshot, "size", [])) if screenshot is not None else None,
            "has_raw_html": bool(sample.get("raw_html")),
            "has_cleaned_html": bool(sample.get("cleaned_html")),
            "cleaned_html_preview": _preview(sample.get("cleaned_html")),
        },
        "action": {
            "type": operation.get("op"),
            "original_type": operation.get("original_op"),
            "value": operation.get("value"),
            "target_action_reprs": sample.get("target_action_reprs"),
            "action_reprs": sample.get("action_reprs") or [],
        },
        "target": {
            "positive_candidates": [_normalize_candidate(candidate) for candidate in pos_candidates],
            "positive_candidates_count": len(pos_candidates),
            "negative_candidates_count": len(neg_candidates),
        },
        "source": {
            "annotation_id": sample.get("annotation_id"),
            "action_uid": action_uid,
            "website": sample.get("website"),
            "domain": sample.get("domain"),
            "subdomain": sample.get("subdomain"),
        },
    }


def _normalize_candidate(candidate: Any) -> dict[str, Any]:
    if isinstance(candidate, str):
        candidate = _parse_json_string(candidate) or {"raw": candidate}
    if not isinstance(candidate, dict):
        return {"raw": candidate}
    attributes = candidate.get("attributes")
    parsed_attributes = _parse_json_string(attributes)
    return {
        "tag": candidate.get("tag"),
        "is_original_target": candidate.get("is_original_target"),
        "is_top_level_target": candidate.get("is_top_level_target"),
        "backend_node_id": candidate.get("backend_node_id") or (parsed_attributes or {}).get("backend_node_id"),
        "bounding_box_rect": (parsed_attributes or {}).get("bounding_box_rect"),
        "attributes": parsed_attributes if parsed_attributes is not None else attributes,
    }


def _save_image(sample: dict[str, Any], image_dir: Path, split: str, index: int) -> Path | None:
    screenshot = sample.get("screenshot")
    if screenshot is None:
        return None
    action_uid = sample.get("action_uid") or f"row-{index}"
    image_path = image_dir / f"{split}_{index:06d}_{action_uid}.jpg"
    screenshot.convert("RGB").save(image_path, quality=90)
    return image_path


def _set_hf_cache_env(cache_root: Path, tmp_dir: Path) -> None:
    cache_root.mkdir(parents=True, exist_ok=True)
    tmp_dir.mkdir(parents=True, exist_ok=True)
    os.environ["HF_HOME"] = str(cache_root.resolve())
    os.environ["HF_HUB_CACHE"] = str((cache_root / "hub").resolve())
    os.environ["HF_DATASETS_CACHE"] = str((cache_root / "datasets").resolve())
    os.environ["HF_XET_CACHE"] = str((cache_root / "xet").resolve())
    os.environ["TEMP"] = str(tmp_dir.resolve())
    os.environ["TMP"] = str(tmp_dir.resolve())


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return _parse_json_string(value) or {}


def _parse_json_string(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _to_int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _preview(value: Any, limit: int = 300) -> str | None:
    if value is None:
        return None
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    text = " ".join(text.split())
    return text[:limit] + ("..." if len(text) > limit else "")


def _relative_or_none(path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        return str(path.relative_to(Path.cwd()))
    except ValueError:
        return str(path)


if __name__ == "__main__":
    raise SystemExit(main())

