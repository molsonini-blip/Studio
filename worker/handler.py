"""
RunPod Serverless worker handler for SadTalker rendering.

Input:
  {
    "portrait_b64": "<base64-encoded PNG>",
    "audio_b64":    "<base64-encoded MP3>",
    "anchor_id":    "marcus_webb"
  }

Output:
  { "mp4_b64": "<base64-encoded MP4>" }
  or on error:
  { "error": "message" }
"""
import base64
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import runpod

WORKER_DIR = Path(__file__).resolve().parent
SADTALKER_DIR = Path("/sadtalker")


def _ensure_models() -> None:
    """Download SadTalker models if not already present (network volume or cold start)."""
    checkpoints = SADTALKER_DIR / "checkpoints"
    print(f"[handler] checkpoints dir: {checkpoints} exists={checkpoints.exists()}")
    if checkpoints.exists() and any(checkpoints.iterdir()):
        print(f"[handler] Models already present: {list(checkpoints.iterdir())[:3]}")
        return

    print("[handler] Downloading SadTalker models...")
    import urllib.request
    checkpoints.mkdir(parents=True, exist_ok=True)
    base_url = "https://github.com/OpenTalker/SadTalker/releases/download/v0.0.2-rc/"
    files = [
        "SadTalker_V0.0.2_256.safetensors",
        "SadTalker_V0.0.2_512.safetensors",
        "mapping_00109-model.pth.tar",
        "mapping_00229-model.pth.tar",
        "facevid2vid_00189-model.pth.tar",
        "auido2exp_00300-model.pth",
        "auido2pose_00140-model.pth",
        "shape_predictor_68_face_landmarks.dat",
        "epoch_20.pth",
    ]
    for fname in files:
        dest = checkpoints / fname
        if not dest.exists():
            print(f"  Downloading {fname}...")
            urllib.request.urlretrieve(f"{base_url}{fname}", str(dest))
    print("[handler] Model download complete.")

    # gfpgan weights
    gfpgan_dir = SADTALKER_DIR / "gfpgan" / "weights"
    gfpgan_dir.mkdir(parents=True, exist_ok=True)


def render(portrait_path: Path, audio_path: Path, out_dir: Path) -> Path:
    before = set(out_dir.rglob("*.mp4"))
    cmd = [
        sys.executable,
        "inference.py",
        "--driven_audio", str(audio_path.resolve()),
        "--source_image", str(portrait_path.resolve()),
        "--result_dir", str(out_dir.resolve()),
        "--still",
        "--preprocess", "crop",
    ]
    result = subprocess.run(
        cmd, capture_output=True, text=True, timeout=600, cwd=str(SADTALKER_DIR)
    )
    if result.returncode != 0:
        raise RuntimeError(f"SadTalker failed (rc={result.returncode}):\n{result.stderr[-3000:]}")
    after = set(out_dir.rglob("*.mp4"))
    new_files = sorted(after - before, key=lambda p: p.stat().st_mtime, reverse=True)
    if not new_files:
        raise RuntimeError(f"SadTalker produced no MP4.\nstdout: {result.stdout[-1000:]}")
    return new_files[0]


def handler(job: dict) -> dict:
    job_input = job["input"]
    anchor_id = job_input.get("anchor_id", "unknown")
    print(f"[handler] Job received: {anchor_id}")

    try:
        _ensure_models()

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)

            portrait_path = tmp / f"{anchor_id}.png"
            audio_path = tmp / f"{anchor_id}.mp3"
            out_dir = tmp / "output"
            out_dir.mkdir()

            portrait_path.write_bytes(base64.b64decode(job_input["portrait_b64"]))
            audio_path.write_bytes(base64.b64decode(job_input["audio_b64"]))

            mp4_path = render(portrait_path, audio_path, out_dir)
            mp4_b64 = base64.b64encode(mp4_path.read_bytes()).decode()
            print(f"[handler] Done: {mp4_path.stat().st_size / 1024:.0f} KB")
            return {"mp4_b64": mp4_b64}

    except Exception as e:
        print(f"[handler] Error: {e}")
        return {"error": str(e)}


if __name__ == "__main__":
    import torch
    print("[handler] Starting RunPod serverless worker...")
    print(f"[handler] SadTalker dir: {SADTALKER_DIR} (exists: {SADTALKER_DIR.exists()})")
    if torch.cuda.is_available():
        print(f"[handler] GPU: {torch.cuda.get_device_name(0)}")
        cap = torch.cuda.get_device_capability(0)
        print(f"[handler] Compute capability: sm_{cap[0]}{cap[1]}")
    else:
        print("[handler] WARNING: CUDA not available")
    runpod.serverless.start({"handler": handler})
