#!/usr/bin/env python3
"""
Download Hallo pretrained models to /hallo/pretrained_models/.

Run this once on a pod with a Network Volume mounted at /hallo/pretrained_models,
then all serverless runs will use the cached models from the volume.

Usage:
    python3 /download_models.py
"""
from huggingface_hub import snapshot_download
from pathlib import Path

MODELS_DIR = Path("/hallo/pretrained_models")
MODELS_DIR.mkdir(parents=True, exist_ok=True)


def dl(repo: str, dest: str, **kwargs) -> None:
    out = MODELS_DIR / dest
    if out.exists() and any(out.iterdir()):
        print(f"[skip] {dest} already exists")
        return
    print(f"[download] {repo} -> pretrained_models/{dest}")
    snapshot_download(repo, local_dir=str(out), ignore_patterns=["*.md", "*.txt"], **kwargs)
    print(f"[done] {dest}")


# Main Hallo checkpoint (~2 GB)
dl("fudan-generative-vision/hallo", "hallo")

# Stable Diffusion v1.5 UNet backbone (~4 GB)
# Hallo uses the UNet + text encoder; skip the ckpt to save ~2 GB
dl(
    "stable-diffusion-v1-5/stable-diffusion-v1-5",
    "stable-diffusion-v1-5",
    ignore_patterns=["*.md", "*.txt", "*.ckpt", "*.png"],
)

# wav2vec2 audio encoder (~360 MB)
dl("facebook/wav2vec2-base-960h", "wav2vec")

# InsightFace buffalo_l face analysis model (~500 MB)
dl(
    "deepinsight/insightface",
    "face_analysis",
    allow_patterns=["models/buffalo_l/*"],
)

print("\nAll models downloaded. Sizes:")
for d in sorted(MODELS_DIR.iterdir()):
    size = sum(f.stat().st_size for f in d.rglob("*") if f.is_file())
    print(f"  {d.name}: {size / 1e9:.1f} GB")
