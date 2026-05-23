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
    """Verify SadTalker models are present (baked into image at build time)."""
    checkpoints = SADTALKER_DIR / "checkpoints"
    files = list(checkpoints.iterdir()) if checkpoints.exists() else []
    print(f"[handler] checkpoints: {len(files)} files — {[f.name for f in files[:4]]}")
    if not files:
        raise RuntimeError(
            "No models found in /sadtalker/checkpoints — image may be stale. Rebuild."
        )


def render(portrait_path: Path, audio_path: Path, out_dir: Path, pose_style: int = 0) -> Path:
    before = set(out_dir.rglob("*.mp4"))
    cmd = [
        sys.executable,
        "inference.py",
        "--driven_audio", str(audio_path.resolve()),
        "--source_image", str(portrait_path.resolve()),
        "--result_dir", str(out_dir.resolve()),
        "--preprocess", "full",
        "--pose_style", str(pose_style),
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


async def handler(job: dict) -> dict:
    import asyncio
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

            pose_style = job_input.get("pose_style", 0)
            print(f"[handler] pose_style={pose_style}")

            # Run blocking SadTalker render in thread so the event loop stays alive
            # (keeps RunPod health pings firing during long GPU inference)
            loop = asyncio.get_event_loop()
            mp4_path = await loop.run_in_executor(
                None, render, portrait_path, audio_path, out_dir, pose_style
            )
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
