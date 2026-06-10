"""Download Qwen-VL-Chat to a project-local models directory.

This script keeps Hugging Face cache, Xet cache, and temporary files under
./models so large model files do not go to the system drive by default.
"""

from __future__ import annotations

import os
from pathlib import Path


MODEL_NAME = "Qwen/Qwen-VL-Chat"
MODELS_DIR = Path("models")
LOCAL_MODEL_DIR = MODELS_DIR / "qwen_vl_chat"
CACHE_ROOT = MODELS_DIR / "huggingface_cache"
TMP_DIR = MODELS_DIR / "tmp"


def main() -> int:
    for path in [LOCAL_MODEL_DIR, CACHE_ROOT, TMP_DIR]:
        path.mkdir(parents=True, exist_ok=True)

    os.environ["HF_HOME"] = str(CACHE_ROOT.resolve())
    os.environ["HF_HUB_CACHE"] = str((CACHE_ROOT / "hub").resolve())
    os.environ["HF_XET_CACHE"] = str((CACHE_ROOT / "xet").resolve())
    os.environ["TRANSFORMERS_CACHE"] = str((CACHE_ROOT / "transformers").resolve())
    os.environ["TEMP"] = str(TMP_DIR.resolve())
    os.environ["TMP"] = str(TMP_DIR.resolve())

    try:
        from huggingface_hub import snapshot_download
    except ImportError as exc:
        raise RuntimeError("huggingface_hub is required. Install it with: pip install huggingface_hub") from exc

    print("model_name:", MODEL_NAME)
    print("local_model_dir:", LOCAL_MODEL_DIR.resolve())
    print("hf_home:", os.environ["HF_HOME"])
    print("hf_hub_cache:", os.environ["HF_HUB_CACHE"])
    print("hf_xet_cache:", os.environ["HF_XET_CACHE"])
    print("tmp_dir:", TMP_DIR.resolve())

    snapshot_download(
        repo_id=MODEL_NAME,
        local_dir=str(LOCAL_MODEL_DIR.resolve()),
        local_dir_use_symlinks=False,
        resume_download=True,
    )

    print("download_complete:", LOCAL_MODEL_DIR.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
