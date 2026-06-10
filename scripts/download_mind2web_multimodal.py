import os
from pathlib import Path


DATASET_NAME = "osunlp/Multimodal-Mind2Web"
RAW_DIR = Path("datasets/raw/Mind2Web")
CACHE_ROOT = RAW_DIR / "huggingface_cache"
TMP_DIR = RAW_DIR / "tmp"

for path in [CACHE_ROOT, TMP_DIR]:
    path.mkdir(parents=True, exist_ok=True)

os.environ["HF_HOME"] = str(CACHE_ROOT.resolve())
os.environ["HF_HUB_CACHE"] = str((CACHE_ROOT / "hub").resolve())
os.environ["HF_DATASETS_CACHE"] = str((CACHE_ROOT / "datasets").resolve())
os.environ["HF_XET_CACHE"] = str((CACHE_ROOT / "xet").resolve())
os.environ["TEMP"] = str(TMP_DIR.resolve())
os.environ["TMP"] = str(TMP_DIR.resolve())

from datasets import load_dataset


ds = load_dataset(
    DATASET_NAME,
    cache_dir=str((CACHE_ROOT / "datasets").resolve()),
)

print(ds)
print("raw_dir:", RAW_DIR)
print("cache_root:", CACHE_ROOT)
print("tmp_dir:", TMP_DIR)
