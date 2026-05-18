"""
Download all required model weights for Studio.

Usage:
    python scripts/download_models.py [--all] [--face-swap] [--sadtalker] [--wav2lip]

Models are saved to the `models/` directory.  HuggingFace weights are cached
via huggingface_hub and will not re-download if already present.
"""
from __future__ import annotations

import argparse
import os
import urllib.request
from pathlib import Path

from huggingface_hub import hf_hub_download, snapshot_download
from tqdm import tqdm

ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / "models"


def _download_url(url: str, dest: Path, desc: str = "") -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        print(f"  [skip] {dest.name} already present")
        return

    print(f"  Downloading {desc or dest.name} …")
    with tqdm(unit="B", unit_scale=True, desc=dest.name) as bar:
        def _progress(count, block, total):
            bar.total = total
            bar.update(block)
        urllib.request.urlretrieve(url, dest, reporthook=_progress)
    print(f"  Saved → {dest}")


# ── Face Swap ─────────────────────────────────────────────────────────────────

def download_face_swap() -> None:
    print("\n[Face Swap] Downloading InsightFace swapper model…")
    dest = MODELS / "face_swap" / "inswapper_128.onnx"
    _download_url(
        "https://huggingface.co/deepinsight/inswapper/resolve/main/inswapper_128.onnx",
        dest,
        "inswapper_128.onnx",
    )

    print("[Face Swap] Downloading GFPGAN enhancer…")
    gfpgan_dest = MODELS / "enhancers" / "GFPGANv1.4.pth"
    _download_url(
        "https://github.com/TencentARC/GFPGAN/releases/download/v1.3.0/GFPGANv1.4.pth",
        gfpgan_dest,
        "GFPGANv1.4.pth",
    )
    print("[Face Swap] Done.")


# ── SadTalker ─────────────────────────────────────────────────────────────────

def download_sadtalker() -> None:
    dest = MODELS / "sadtalker"

    # Clone the repo first (gets inference.py and the correct directory layout)
    if not (dest / "inference.py").exists():
        print("\n[SadTalker] Cloning SadTalker repo…")
        os.system(f'git clone --depth 1 https://github.com/OpenTalker/SadTalker.git "{dest}"')
    else:
        print("\n[SadTalker] Repo already cloned.")

    checkpoints_dir = dest / "checkpoints"
    checkpoints_dir.mkdir(parents=True, exist_ok=True)

    # Individual model files — vinthony/SadTalker HF repo (flat layout, no longer bundled)
    print("[SadTalker] Downloading model checkpoints from HuggingFace…")
    checkpoint_files = [
        "auido2exp_00300-model.pth",
        "auido2pose_00140-model.pth",
        "epoch_20.pth",
        "facevid2vid_00189-model.pth.tar",
        "mapping_00109-model.pth.tar",
        "mapping_00229-model.pth.tar",
        "shape_predictor_68_face_landmarks.dat",
        "wav2lip.pth",
    ]
    for filename in checkpoint_files:
        out = checkpoints_dir / filename
        if out.exists():
            print(f"  [skip] {filename}")
            continue
        print(f"  {filename}")
        hf_hub_download(repo_id="vinthony/SadTalker", filename=filename, local_dir=str(checkpoints_dir))

    # BFM Fitting directory (3D morphable model data)
    print("[SadTalker] Downloading BFM Fitting data…")
    bfm_dir = checkpoints_dir / "BFM_Fitting"
    bfm_dir.mkdir(exist_ok=True)
    bfm_files = [
        "BFM_Fitting/01_MorphableModel.mat",
        "BFM_Fitting/BFM09_model_info.mat",
        "BFM_Fitting/BFM_exp_idx.mat",
        "BFM_Fitting/BFM_front_idx.mat",
        "BFM_Fitting/Exp_Pca.bin",
        "BFM_Fitting/facemodel_info.mat",
        "BFM_Fitting/select_vertex_id.mat",
        "BFM_Fitting/similarity_Lm3D_all.mat",
        "BFM_Fitting/std_exp.txt",
    ]
    for filename in bfm_files:
        basename = Path(filename).name
        out = bfm_dir / basename
        if out.exists():
            print(f"  [skip] {basename}")
            continue
        print(f"  {basename}")
        hf_hub_download(repo_id="vinthony/SadTalker", filename=filename, local_dir=str(checkpoints_dir))

    # GFPGAN face detection weights (used by SadTalker's enhancer)
    print("[SadTalker] Downloading GFPGAN weights…")
    gfpgan_dir = dest / "gfpgan" / "weights"
    gfpgan_dir.mkdir(parents=True, exist_ok=True)
    gfpgan_files = [
        ("xinntao/facexlib", "weights/detection_Resnet50_Final.pth"),
        ("xinntao/facexlib", "weights/parsing_parsenet.pth"),
        ("TencentARC/GFPGAN", "experiments/pretrained_models/GFPGANv1.4.pth"),
    ]
    for repo_id, filename in gfpgan_files:
        basename = Path(filename).name
        out = gfpgan_dir / basename
        if out.exists():
            print(f"  [skip] {basename}")
            continue
        print(f"  {basename}")
        hf_hub_download(repo_id=repo_id, filename=filename, local_dir=str(gfpgan_dir))

    print("[SadTalker] Done.")


# ── Wav2Lip ───────────────────────────────────────────────────────────────────

def download_wav2lip() -> None:
    print("\n[Wav2Lip] Downloading checkpoint…")
    dest = MODELS / "wav2lip" / "wav2lip_gan.pth"
    _download_url(
        "https://iiitaphyd-my.sharepoint.com/personal/radrabha_m_research_iiit_ac_in/"
        "_layouts/15/download.aspx?share=EdjI7bZlgApMqsVoEUUXpLsBxqXbn5z8VvmAmRkDRLWRzg",
        dest,
        "wav2lip_gan.pth",
    )

    wav2lip_dir = MODELS / "wav2lip"
    if not (wav2lip_dir / "inference.py").exists():
        print("  Cloning Wav2Lip repo…")
        os.system(f'git clone --depth 1 https://github.com/Rudrabha/Wav2Lip.git "{wav2lip_dir}"')
    print("[Wav2Lip] Done.")


# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Download Studio model weights")
    parser.add_argument("--all", action="store_true", help="Download everything")
    parser.add_argument("--face-swap", action="store_true")
    parser.add_argument("--sadtalker", action="store_true")
    parser.add_argument("--wav2lip", action="store_true")
    args = parser.parse_args()

    if not any(vars(args).values()):
        parser.print_help()
        return

    if args.all or args.face_swap:
        download_face_swap()
    if args.all or args.sadtalker:
        download_sadtalker()
    if args.all or args.wav2lip:
        download_wav2lip()

    print("\nAll requested models downloaded.")


if __name__ == "__main__":
    main()
