"""Inspect raw ScreenAgent and Multimodal-Mind2Web datasets."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any


MIND2WEB_DATASET = "osunlp/Multimodal-Mind2Web"
MIND2WEB_SPLITS = ["train", "test_task", "test_website", "test_domain"]
DEFAULT_SCREENAGENT_DIR = Path("datasets/raw/ScreenAgent")
DEFAULT_MIND2WEB_DIR = Path("datasets/raw/Mind2Web")
PREVIEW_LIMIT = 180


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect local raw GUI-agent datasets.")
    parser.add_argument("--screenagent-dir", default=str(DEFAULT_SCREENAGENT_DIR))
    parser.add_argument("--mind2web-dir", default=str(DEFAULT_MIND2WEB_DIR))
    parser.add_argument("--skip-screenagent", action="store_true")
    parser.add_argument("--skip-mind2web", action="store_true")
    args = parser.parse_args()

    if not args.skip_screenagent:
        inspect_screenagent(Path(args.screenagent_dir))
    if not args.skip_mind2web:
        inspect_mind2web(Path(args.mind2web_dir))
    return 0


def inspect_screenagent(root: Path) -> None:
    print("\n=== ScreenAgent ===")
    print("root:", root)
    if not root.exists():
        print("status: missing")
        return

    for split in ["train", "test"]:
        split_dir = root / split
        print(f"\n[{split}]")
        if not split_dir.exists():
            print("status: missing")
            continue

        sessions = sorted(path for path in split_dir.rglob("*") if path.is_dir() and (path / "images").exists())
        json_files = sorted(split_dir.rglob("*.json"))
        image_files = sorted(
            path for pattern in ("*.jpg", "*.jpeg", "*.png") for path in split_dir.rglob(pattern)
        )
        print("session_count:", len(sessions))
        print("json_file_count:", len(json_files))
        print("image_file_count:", len(image_files))

        sample_json = _first_json(json_files)
        if sample_json is None:
            print("sample: no json file found")
            continue
        print("sample_json:", sample_json)
        sample = _read_json(sample_json)
        print("sample_fields:", sorted(sample.keys()))
        print("sample_summary:", _summarize_screenagent_sample(sample))


def inspect_mind2web(root: Path) -> None:
    print("\n=== Multimodal-Mind2Web ===")
    print("root:", root)
    cache_root = root / "huggingface_cache"
    tmp_dir = root / "tmp"
    print("cache_root:", cache_root)
    print("tmp_dir:", tmp_dir)
    if not cache_root.exists():
        print("status: missing cache; run scripts/download_mind2web_multimodal.py first")
        return

    _set_hf_cache_env(cache_root, tmp_dir)

    from datasets import load_dataset

    for split in MIND2WEB_SPLITS:
        print(f"\n[{split}]")
        dataset = load_dataset(
            MIND2WEB_DATASET,
            split=split,
            cache_dir=str((cache_root / "datasets").resolve()),
        )
        print("row_count:", len(dataset))
        print("features:", list(dataset.features.keys()))
        if len(dataset) == 0:
            continue
        sample = dataset[0]
        print("sample_summary:", _summarize_mind2web_sample(sample))


def _set_hf_cache_env(cache_root: Path, tmp_dir: Path) -> None:
    cache_root.mkdir(parents=True, exist_ok=True)
    tmp_dir.mkdir(parents=True, exist_ok=True)
    os.environ["HF_HOME"] = str(cache_root.resolve())
    os.environ["HF_HUB_CACHE"] = str((cache_root / "hub").resolve())
    os.environ["HF_DATASETS_CACHE"] = str((cache_root / "datasets").resolve())
    os.environ["HF_XET_CACHE"] = str((cache_root / "xet").resolve())
    os.environ["TEMP"] = str(tmp_dir.resolve())
    os.environ["TMP"] = str(tmp_dir.resolve())


def _first_json(paths: list[Path]) -> Path | None:
    for path in paths:
        if path.name.endswith(".json"):
            return path
    return None


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _summarize_screenagent_sample(sample: dict[str, Any]) -> dict[str, Any]:
    actions = sample.get("actions")
    return {
        "session_id": sample.get("session_id"),
        "task_prompt": _preview(sample.get("task_prompt")),
        "task_prompt_en": _preview(sample.get("task_prompt_en")),
        "task_prompt_zh": _preview(sample.get("task_prompt_zh")),
        "saved_image_name": sample.get("saved_image_name"),
        "video_size": [sample.get("video_width"), sample.get("video_height")],
        "actions_type": type(actions).__name__,
        "actions_count": len(actions) if isinstance(actions, list) else None,
        "first_action": _preview(actions[0]) if isinstance(actions, list) and actions else None,
    }


def _summarize_mind2web_sample(sample: dict[str, Any]) -> dict[str, Any]:
    pos_candidates = sample.get("pos_candidates") or []
    neg_candidates = sample.get("neg_candidates") or []
    screenshot = sample.get("screenshot")
    return {
        "annotation_id": sample.get("annotation_id"),
        "action_uid": sample.get("action_uid"),
        "website": sample.get("website"),
        "domain": sample.get("domain"),
        "confirmed_task": _preview(sample.get("confirmed_task")),
        "operation": sample.get("operation"),
        "target_action_index": sample.get("target_action_index"),
        "target_action_reprs": _preview(sample.get("target_action_reprs")),
        "action_reprs_count": len(sample.get("action_reprs") or []),
        "has_raw_html": bool(sample.get("raw_html")),
        "has_cleaned_html": bool(sample.get("cleaned_html")),
        "screenshot_type": type(screenshot).__name__,
        "screenshot_size": getattr(screenshot, "size", None),
        "pos_candidates_count": len(pos_candidates),
        "neg_candidates_count": len(neg_candidates),
        "first_pos_candidate": _preview(pos_candidates[0]) if pos_candidates else None,
    }


def _preview(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (int, float, bool)):
        return value
    text = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
    text = " ".join(text.split())
    return text[:PREVIEW_LIMIT] + ("..." if len(text) > PREVIEW_LIMIT else "")


if __name__ == "__main__":
    raise SystemExit(main())
