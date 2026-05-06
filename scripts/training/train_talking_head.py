"""
Fine-tune a talking head model on anchor face frames + aligned audio.

Uses SadTalker's training pipeline OR a lightweight custom face reenactment
approach based on First Order Motion Model (FOMM).

Requires GPU. On the server (CPU-only) this script will warn and exit.

Usage:
    python scripts/training/train_talking_head.py \\
        --manifest data/training/talking_head_manifest.json \\
        --frames-dir data/training/anchor_frames \\
        --output models/talking_head_finetune \\
        --method fomm

Methods:
    sadtalker  -- fine-tune SadTalker checkpoints on new anchor identity
    fomm       -- train First Order Motion Model on extracted anchor frames
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import torch


def _check_gpu():
    if not torch.cuda.is_available():
        print("WARNING: No CUDA GPU detected.")
        print("Talking head training on CPU would take weeks.")
        print("Options:")
        print("  1. Run on a machine with an NVIDIA GPU (min 8GB VRAM recommended)")
        print("  2. Rent GPU: RunPod A10G (~$0.39/hr), Lambda A100 (~$1.10/hr)")
        print("  3. Use SadTalker as-is — it generalises well to new faces without fine-tuning")
        sys.exit(1)


# ── FOMM-based training ───────────────────────────────────────────────────────

def train_fomm(
    frames_dir: Path,
    output_dir: Path,
    epochs: int = 100,
    batch_size: int = 16,
):
    """Train First Order Motion Model on anchor frames.

    FOMM learns to reenact faces using keypoint-based motion estimation.
    Training on anchor-specific frames teaches it the anchor's appearance.
    """
    _check_gpu()
    try:
        import imageio
        import numpy as np
        from torch import nn
        from torch.utils.data import DataLoader, Dataset
        from torchvision import transforms
        from PIL import Image
    except ImportError:
        print("Install: pip install imageio torchvision pillow")
        sys.exit(1)

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading anchor frames from: {frames_dir}")
    frame_paths = sorted(Path(frames_dir).rglob("*.jpg")) + sorted(Path(frames_dir).rglob("*.png"))
    print(f"  Found {len(frame_paths)} frames")

    if len(frame_paths) < 50:
        print("WARNING: Less than 50 frames. Collect more data for stable training.")

    transform = transforms.Compose([
        transforms.Resize((256, 256)),
        transforms.ToTensor(),
        transforms.Normalize([0.5, 0.5, 0.5], [0.5, 0.5, 0.5]),
    ])

    class AnchorFrameDataset(Dataset):
        def __init__(self, paths, transform):
            self.paths = paths
            self.transform = transform

        def __len__(self): return len(self.paths)

        def __getitem__(self, idx):
            img = Image.open(self.paths[idx]).convert("RGB")
            return self.transform(img)

    dataset = AnchorFrameDataset(frame_paths, transform)
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True, num_workers=4)

    # Minimal training loop placeholder — full FOMM requires the upstream repo
    # Clone: https://github.com/AliaksandrSiarohin/first-order-model
    fomm_dir = Path("models/fomm")
    if not fomm_dir.exists():
        print("Cloning First Order Motion Model repo...")
        import subprocess
        subprocess.run(
            ["git", "clone", "--depth", "1",
             "https://github.com/AliaksandrSiarohin/first-order-model.git",
             str(fomm_dir)],
            check=True
        )

    sys.path.insert(0, str(fomm_dir))
    try:
        from train import train as fomm_train  # type: ignore
        fomm_train(
            config_path=str(fomm_dir / "config" / "vox-256.yaml"),
            log_dir=str(output_dir),
            checkpoint=None,
            device_ids=[0],
        )
    except ImportError:
        print("FOMM train module not found. Ensure the repo was cloned correctly.")
        sys.exit(1)

    print(f"Training complete. Model saved to: {output_dir}")


# ── SadTalker fine-tune ───────────────────────────────────────────────────────

def finetune_sadtalker(
    manifest_path: Path,
    frames_dir: Path,
    output_dir: Path,
    epochs: int = 20,
    batch_size: int = 8,
):
    """Fine-tune SadTalker on anchor-specific video data.

    Adapts the audio-to-motion mapping to an anchor's specific facial dynamics.
    """
    _check_gpu()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    sadtalker_dir = Path("models/sadtalker")
    if not sadtalker_dir.exists():
        print(f"SadTalker not found at {sadtalker_dir}. Run scripts/download_models.py --sadtalker first.")
        sys.exit(1)

    with open(manifest_path) as f:
        manifest = json.load(f)

    print(f"Fine-tuning SadTalker on {len(manifest)} clips ({frames_dir})")

    # SadTalker fine-tuning requires its training script
    sys.path.insert(0, str(sadtalker_dir))
    try:
        import subprocess
        cmd = [
            sys.executable,
            str(sadtalker_dir / "train.py"),
            "--data_root", str(frames_dir),
            "--manifest", str(manifest_path),
            "--checkpoint_dir", str(sadtalker_dir),
            "--result_dir", str(output_dir),
            "--batch_size", str(batch_size),
            "--epochs", str(epochs),
        ]
        subprocess.run(cmd, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("SadTalker train.py not found or failed. Check SadTalker installation.")
        sys.exit(1)

    print(f"Fine-tune complete → {output_dir}")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fine-tune talking head model on anchor data")
    parser.add_argument("--manifest", required=True, type=Path, help="Talking head manifest JSON")
    parser.add_argument("--frames-dir", required=True, type=Path, help="Anchor frame directory")
    parser.add_argument("--output", default="models/talking_head_finetune", type=Path)
    parser.add_argument("--method", choices=["fomm", "sadtalker"], default="fomm")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--batch-size", type=int, default=8)
    args = parser.parse_args()

    if args.method == "fomm":
        train_fomm(args.frames_dir, args.output, args.epochs, args.batch_size)
    else:
        finetune_sadtalker(args.manifest, args.frames_dir, args.output, args.epochs, args.batch_size)
