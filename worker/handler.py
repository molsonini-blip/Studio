"""
RunPod Serverless worker handler for MuseTalk portrait animation.

Input:
  {
    "portrait_b64": "<base64 PNG>",
    "audio_b64":    "<base64 MP3>",
    "anchor_id":    "marcus_webb"
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

MUSETALK_DIR = Path("/musetalk")
MODELS_DIR   = MUSETALK_DIR / "models"


def _check_models() -> None:
    required = [
        MODELS_DIR / "musetalk",
        MODELS_DIR / "whisper",
        MODELS_DIR / "dwpose",
        MODELS_DIR / "sd-vae-ft-mse",
    ]
    missing = [str(p) for p in required if not p.exists()]
    if missing:
        raise RuntimeError(f"Missing MuseTalk models: {missing} — rebuild image.")
    print(f"[handler] Models OK: {[p.name for p in required]}")


def _convert_audio(mp3_path: Path, wav_path: Path) -> None:
    result = subprocess.run(
        ["ffmpeg", "-y", "-i", str(mp3_path), "-ar", "16000", "-ac", "1", str(wav_path)],
        capture_output=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Audio conversion failed:\n{result.stderr.decode(errors='replace')}"
        )


def render(portrait_path: Path, audio_wav: Path, result_dir: Path) -> Path:
    cmd = [
        sys.executable, "-m", "scripts.inference",
        "--video_path",  str(portrait_path),
        "--audio_path",  str(audio_wav),
        "--result_dir",  str(result_dir),
        "--fps",         "25",
        "--use_float16",
    ]
    result = subprocess.run(
        cmd, capture_output=True, text=True, timeout=600, cwd=str(MUSETALK_DIR)
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"MuseTalk failed (rc={result.returncode}):\n{result.stderr[-3000:]}"
        )
    # MuseTalk writes output somewhere under result_dir — find newest MP4
    mp4s = sorted(result_dir.rglob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
    if mp4s:
        return mp4s[0]
    raise RuntimeError(f"MuseTalk produced no output.\nstdout: {result.stdout[-1000:]}")


async def handler(job: dict) -> dict:
    job_input = job["input"]
    anchor_id = job_input.get("anchor_id", "unknown")
    print(f"[handler] Job received: {anchor_id}")

    try:
        _check_models()

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            result_dir = tmp / "results"
            result_dir.mkdir()

            portrait_path = tmp / f"{anchor_id}.png"
            audio_mp3     = tmp / f"{anchor_id}.mp3"
            audio_wav     = tmp / f"{anchor_id}.wav"

            portrait_path.write_bytes(base64.b64decode(job_input["portrait_b64"]))
            audio_mp3.write_bytes(base64.b64decode(job_input["audio_b64"]))

            _convert_audio(audio_mp3, audio_wav)

            loop = asyncio.get_event_loop()
            mp4_path = await loop.run_in_executor(
                None, render, portrait_path, audio_wav, result_dir
            )
            mp4_b64 = base64.b64encode(mp4_path.read_bytes()).decode()
            print(f"[handler] Done: {mp4_path.stat().st_size / 1024:.0f} KB")
            return {"mp4_b64": mp4_b64}

    except Exception as e:
        print(f"[handler] Error: {e}")
        return {"error": str(e)}


if __name__ == "__main__":
    import torch
    print("[handler] Starting MuseTalk RunPod worker...")
    print(f"[handler] MuseTalk dir: {MUSETALK_DIR} (exists={MUSETALK_DIR.exists()})")
    print(f"[handler] Models dir:   {MODELS_DIR} (exists={MODELS_DIR.exists()})")
    if torch.cuda.is_available():
        print(f"[handler] GPU: {torch.cuda.get_device_name(0)}")
        cap = torch.cuda.get_device_capability(0)
        print(f"[handler] Compute capability: sm_{cap[0]}{cap[1]}")
    else:
        print("[handler] WARNING: CUDA not available")
    runpod.serverless.start({"handler": handler})
