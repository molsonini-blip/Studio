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
    print("\n[SadTalker] Downloading checkpoints from HuggingFace…")
    dest = MODELS / "sadtalker"
    dest.mkdir(parents=True, exist_ok=True)

    files = [
        ("vinthony/SadTalker", "checkpoints/SadTalker_V0.0.2_256.safetensors"),
        ("vinthony/SadTalker", "checkpoints/mapping_00109-model.pth.tar"),
        ("vinthony/SadTalker", "checkpoints/mapping_00229-model.pth.tar"),
        ("vinthony/SadTalker", "gfpgan/weights/detection_Resnet50_Final.pth"),
        ("vinthony/SadTalker", "gfpgan/weights/parsing_parsenet.pth"),
    ]
    for repo_id, filename in files:
        out = dest / Path(filename).name
        if out.exists():
            print(f"  [skip] {out.name}")
            continue
        print(f"  {filename}")
        hf_hub_download(repo_id=repo_id, filename=filename, local_dir=str(dest))

    # Clone inference script if not present
    sadtalker_script = dest / "inference.py"
    if not sadtalker_script.exists():
        print("  Cloning SadTalker repo for inference scripts…")
        os.system(f'git clone --depth 1 https://github.com/OpenTalker/SadTalker.git "{dest}"')
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
