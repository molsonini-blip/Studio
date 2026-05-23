"""
RunPod Serverless worker handler for Hallo portrait animation.

Input:
  {
    "portrait_b64": "<base64 PNG>",
    "audio_b64":    "<base64 MP3>",
    "anchor_id":    "marcus_webb",
    "lip_weight":   1.0,
    "face_weight":  1.0,
    "pose_weight":  1.0
  }

Output:
  { "mp4_b64": "<base64 MP4>" }
  or on error:
  { "error": "message" }
"""
import asyncio
import base64
import subprocess
import sys
import tempfile
from pathlib import Path

import runpod

HALLO_DIR = Path("/hallo")
MODELS_DIR = HALLO_DIR / "pretrained_models"


def _check_models() -> None:
    """Verify required Hallo model directories are present."""
    required = [
        MODELS_DIR / "hallo",
        MODELS_DIR / "stable-diffusion-v1-5",
        MODELS_DIR / "face_analysis",
        MODELS_DIR / "wav2vec",
    ]
    missing = [str(p) for p in required if not p.exists()]
    if missing:
        raise RuntimeError(f"Missing Hallo models: {missing} — rebuild image.")
    print(f"[handler] Models OK: {[p.name for p in required]}")


def _convert_audio(mp3_path: Path, wav_path: Path) -> None:
    """Convert MP3 to WAV 16 kHz mono (Hallo requirement)."""
    result = subprocess.run(
        ["ffmpeg", "-y", "-i", str(mp3_path), "-ar", "16000", "-ac", "1", str(wav_path)],
        capture_output=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Audio conversion failed:\n{result.stderr.decode(errors='replace')}"
        )


def render(
    portrait_path: Path,
    audio_wav: Path,
    output_path: Path,
    lip_weight: float = 1.0,
    face_weight: float = 1.0,
    pose_weight: float = 1.0,
) -> Path:
    cmd = [
        sys.executable, "scripts/inference.py",
        "--source_image", str(portrait_path),
        "--driving_audio", str(audio_wav),
        "--output", str(output_path),
        "--lip_weight", str(lip_weight),
        "--face_weight", str(face_weight),
        "--pose_weight", str(pose_weight),
    ]
    result = subprocess.run(
        cmd, capture_output=True, text=True, timeout=1200, cwd=str(HALLO_DIR)
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Hallo failed (rc={result.returncode}):\n{result.stderr[-3000:]}"
        )
    if output_path.exists():
        return output_path
    # Fallback: Hallo sometimes writes to .cache/output.mp4
    fallback = HALLO_DIR / ".cache" / "output.mp4"
    if fallback.exists():
        return fallback
    raise RuntimeError(f"Hallo produced no output.\nstdout: {result.stdout[-1000:]}")


async def handler(job: dict) -> dict:
    job_input = job["input"]
    anchor_id = job_input.get("anchor_id", "unknown")
    print(f"[handler] Job received: {anchor_id}")

    try:
        _check_models()

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)

            portrait_path = tmp / f"{anchor_id}.png"
            audio_mp3    = tmp / f"{anchor_id}.mp3"
            audio_wav    = tmp / f"{anchor_id}.wav"
            output_path  = tmp / f"{anchor_id}_hallo.mp4"

            portrait_path.write_bytes(base64.b64decode(job_input["portrait_b64"]))
            audio_mp3.write_bytes(base64.b64decode(job_input["audio_b64"]))

            _convert_audio(audio_mp3, audio_wav)

            lip_weight  = float(job_input.get("lip_weight",  1.0))
            face_weight = float(job_input.get("face_weight", 1.0))
            pose_weight = float(job_input.get("pose_weight", 1.0))
            print(f"[handler] weights — lip={lip_weight} face={face_weight} pose={pose_weight}")

            # Run Hallo in a thread so the event loop keeps firing RunPod health pings
            loop = asyncio.get_event_loop()
            mp4_path = await loop.run_in_executor(
                None, render,
                portrait_path, audio_wav, output_path,
                lip_weight, face_weight, pose_weight,
            )
            mp4_b64 = base64.b64encode(mp4_path.read_bytes()).decode()
            print(f"[handler] Done: {mp4_path.stat().st_size / 1024:.0f} KB")
            return {"mp4_b64": mp4_b64}

    except Exception as e:
        print(f"[handler] Error: {e}")
        return {"error": str(e)}


if __name__ == "__main__":
    import torch
    print("[handler] Starting Hallo RunPod worker...")
    print(f"[handler] Hallo dir: {HALLO_DIR} (exists={HALLO_DIR.exists()})")
    print(f"[handler] Models dir: {MODELS_DIR} (exists={MODELS_DIR.exists()})")
    if torch.cuda.is_available():
        print(f"[handler] GPU: {torch.cuda.get_device_name(0)}")
        cap = torch.cuda.get_device_capability(0)
        print(f"[handler] Compute capability: sm_{cap[0]}{cap[1]}")
    else:
        print("[handler] WARNING: CUDA not available")
    runpod.serverless.start({"handler": handler})
