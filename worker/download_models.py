#!/usr/bin/env python3
"""
Download MuseTalk pretrained models to /musetalk/models/.

Run this once on a pod with a Network Volume mounted at /musetalk/models,
then all serverless runs will use the cached models from the volume.

Usage:
    python3 /download_models.py
"""
from huggingface_hub import snapshot_download
from pathlib import Path

MODELS_DIR = Path("/musetalk/models")
MODELS_DIR.mkdir(parents=True, exist_ok=True)

print("[download] Pulling TMElyralab/MuseTalk (~5 GB)...")
snapshot_download(
    "TMElyralab/MuseTalk",
    local_dir=str(MODELS_DIR),
    ignore_patterns=["*.md"],
)
print("[done] All MuseTalk models downloaded.")

print("\nModel sizes:")
for d in sorted(MODELS_DIR.iterdir()):
    if d.is_dir():
        size = sum(f.stat().st_size for f in d.rglob("*") if f.is_file())
        print(f"  {d.name}: {size / 1e9:.1f} GB")
