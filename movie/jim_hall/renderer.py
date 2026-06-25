"""
Jim Hall movie — RunPod GPU renderer.

Spins up a RunPod GPU pod, uploads the render script, executes it to generate
FLUX images and/or CogVideoX video clips for each scene, then downloads results.

Workflow:
  1. Create pod (RTX 4090 or A100 — picks cheapest available)
  2. Wait for SSH
  3. Install dependencies (diffusers, transformers, cogvideo)
  4. Upload render job JSON
  5. Run render script on pod
  6. Download outputs (PNG images + MP4 clips)
  7. Terminate pod

Outputs land in:
  outputs/jim_hall/images/{scene_id:02d}_{slug}/
  outputs/jim_hall/video/{scene_id:02d}_{slug}.mp4
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

from core.production.runpod_manager import RunPodManager

# GPU preference for movie work — cheapest that can run FLUX + CogVideoX
# CogVideoX-5B needs ~16GB VRAM; FLUX schnell needs ~12GB
# IDs must match exactly what RunPod's gpuTypes API returns in the 'id' field
MOVIE_GPU_TYPES = [
    # 24GB options — ideal for both FLUX and CogVideoX
    "NVIDIA GeForce RTX 4090",
    "NVIDIA GeForce RTX 3090",
    "NVIDIA GeForce RTX 3090 Ti",
    "NVIDIA RTX A5000",
    "NVIDIA RTX 5000 Ada Generation",
    # 20GB options — good for FLUX, minimum for CogVideoX
    "NVIDIA RTX 4000 Ada Generation",
    "NVIDIA RTX 4000 SFF Ada Generation",
    "NVIDIA RTX A4500",
    # 16GB options — FLUX only (CogVideoX will use CPU offload)
    "NVIDIA GeForce RTX 4080",
    "NVIDIA GeForce RTX 4080 SUPER",
    "NVIDIA RTX A4000",
    # 48GB+ options — expensive but available when others are not
    "NVIDIA RTX A6000",
    "NVIDIA RTX 6000 Ada Generation",
    "NVIDIA L40",
    "NVIDIA L40S",
    "NVIDIA A40",
    "NVIDIA A100 80GB PCIe",
    "NVIDIA A100-SXM4-80GB",
]

# Remote paths on the pod
REMOTE_STUDIO = "/workspace/studio"
REMOTE_RENDER_SCRIPT = f"{REMOTE_STUDIO}/scripts/jim_hall_render_gpu.py"
REMOTE_JOB_FILE = f"{REMOTE_STUDIO}/jim_hall_job.json"
REMOTE_OUTPUTS = f"{REMOTE_STUDIO}/outputs/jim_hall_gpu"

# SSH key path
SSH_KEY = Path.home() / ".ssh" / "id_ed25519"
SSH_KEY_ALT = Path("C:/Users/olson/OneDrive/.ssh/id_ed25519")


def _find_ssh_key() -> Path:
    for p in [SSH_KEY, SSH_KEY_ALT]:
        if p.exists():
            return p
    raise FileNotFoundError(f"SSH key not found at {SSH_KEY} or {SSH_KEY_ALT}")


def _build_job(scenes: list[dict], mode: str) -> dict:
    """Build the job payload for the GPU render script."""
    jobs = []
    for scene in scenes:
        job = {
            "id": scene["id"],
            "slug": scene["slug"],
            "title": scene["title"],
            "priority": scene.get("priority", "MEDIUM"),
            "image_prompts": scene.get("image_prompts", []),
            "video_prompt": scene.get("video_prompt", ""),
            "video_negative": scene.get("video_negative", ""),
            "duration_sec": scene.get("duration_sec", 60),
        }
        jobs.append(job)
    return {"mode": mode, "jobs": jobs}


def render_images(
    scenes: list[dict],
    output_root: Path,
    api_key: str | None = None,
    images_per_scene: int = 3,
    priority_only: bool = True,
    max_wait_minutes: int = 120,
) -> dict[int, list[Path]]:
    """
    Generate FLUX images for each scene on RunPod.
    Returns {scene_id: [image_paths]}.
    """
    # Filter to high-priority scenes if requested
    if priority_only:
        scenes = [s for s in scenes if s.get("priority") in ("HIGH", "HIGHEST")]
        print(f"[renderer] Priority filter: {len(scenes)} scenes")

    return _run_on_pod(scenes, "images", output_root, api_key, images_per_scene, max_wait_minutes)


def render_video(
    scenes: list[dict],
    output_root: Path,
    api_key: str | None = None,
    priority_only: bool = True,
) -> dict[int, Path]:
    """
    Generate CogVideoX video clips for each scene on RunPod.
    Returns {scene_id: video_path}.
    """
    if priority_only:
        scenes = [s for s in scenes if s.get("priority") in ("HIGH", "HIGHEST")]
        print(f"[renderer] Priority filter: {len(scenes)} scenes")

    return _run_on_pod(scenes, "video", output_root, api_key)


def _run_on_pod(
    scenes: list[dict],
    mode: str,
    output_root: Path,
    api_key: str | None = None,
    images_per_scene: int = 3,
    max_wait_minutes: int = 120,
) -> dict:
    api_key = api_key or os.environ.get("RUNPOD_API_KEY")
    if not api_key:
        raise RuntimeError("RUNPOD_API_KEY not set")

    ssh_key = _find_ssh_key()
    mgr = RunPodManager(api_key=api_key, gpu_type=MOVIE_GPU_TYPES[0])
    mgr.gpu_types = MOVIE_GPU_TYPES

    local_render_script = Path(__file__).resolve().parents[2] / "scripts" / "jim_hall_render_gpu.py"

    results: dict = {}
    pod_id = None

    try:
        # ── 1. Start pod (with retry) ─────────────────────────────────────────
        print(f"\n[renderer] Starting RunPod GPU pod for {mode} render ({len(scenes)} scenes)...")
        deadline = time.time() + (max_wait_minutes * 60)
        retry_interval = 60  # start at 1 minute, back off to 5 min
        while True:
            try:
                pod_id = mgr.create_pod()
                break
            except RuntimeError as e:
                if "No GPU available" not in str(e):
                    raise
                if time.time() > deadline:
                    raise RuntimeError(
                        f"[renderer] GPU market fully sold out after {max_wait_minutes} min. "
                        "Try again later or run --render-images --gpu-wait-hours 8 overnight."
                    ) from e
                wait_min = retry_interval / 60
                print(f"[renderer] All GPUs sold out. Retrying in {wait_min:.0f} min... "
                      f"(will keep trying for {(deadline-time.time())/60:.0f} more min)")
                time.sleep(retry_interval)
                retry_interval = min(retry_interval * 1.5, 300)  # cap at 5 min

        host, port = mgr.wait_for_ssh(timeout=300, key_path=ssh_key)
        print(f"[renderer] Pod ready: {host}:{port}")

        # ── 2. Install deps ───────────────────────────────────────────────────
        print("[renderer] Installing GPU dependencies...")
        mgr.run(
            "pip install -q --upgrade diffusers transformers accelerate "
            "huggingface_hub safetensors imageio imageio-ffmpeg opencv-python-headless "
            "sentencepiece protobuf 2>&1 | tail -5",
            key_path=ssh_key,
        )
        # CogVideoX needs this specific package
        if mode == "video":
            mgr.run(
                "pip install -q 'git+https://github.com/huggingface/diffusers.git' 2>&1 | tail -3",
                key_path=ssh_key,
            )

        # ── 3. Upload script and job ──────────────────────────────────────────
        print("[renderer] Uploading render script and job data...")
        mgr.run(f"mkdir -p {REMOTE_STUDIO}/scripts {REMOTE_OUTPUTS}", key_path=ssh_key)
        mgr.upload(local_render_script, REMOTE_RENDER_SCRIPT, key_path=ssh_key)

        job = _build_job(scenes, mode)
        job["images_per_scene"] = images_per_scene
        job_json = json.dumps(job, indent=2)

        # Write job file remotely
        escaped = job_json.replace("'", "'\"'\"'")
        mgr.run(f"echo '{escaped}' > {REMOTE_JOB_FILE}", key_path=ssh_key)

        # ── 4. Execute render ─────────────────────────────────────────────────
        print(f"[renderer] Running {mode} render on GPU...")
        t0 = time.time()

        # Stream output via long SSH command
        # Estimate time: images ~30s/scene, video ~3min/scene
        est_min = (0.5 if mode == "images" else 3) * len(scenes)
        print(f"[renderer] Estimated time: {est_min:.0f}–{est_min*2:.0f} min")

        out, _ = mgr.run(
            f"cd {REMOTE_STUDIO} && python {REMOTE_RENDER_SCRIPT} "
            f"--job {REMOTE_JOB_FILE} --output {REMOTE_OUTPUTS} 2>&1",
            key_path=ssh_key,
        )
        elapsed = time.time() - t0
        print(f"[renderer] GPU render done in {elapsed/60:.1f} min")
        print(out[-2000:])  # last 2000 chars of output

        # ── 5. Download outputs ───────────────────────────────────────────────
        print("[renderer] Downloading outputs from pod...")
        local_gpu_dir = output_root / f"gpu_{mode}"
        local_gpu_dir.mkdir(parents=True, exist_ok=True)
        mgr.download_dir(REMOTE_OUTPUTS, local_gpu_dir, key_path=ssh_key)

        print(f"[renderer] Downloaded to {local_gpu_dir}")

        # ── 6. Map outputs to scene IDs ───────────────────────────────────────
        for scene in scenes:
            sid = scene["id"]
            slug = scene["slug"]
            if mode == "images":
                img_dir = local_gpu_dir / f"{sid:02d}_{slug}"
                if img_dir.exists():
                    results[sid] = sorted(img_dir.glob("*.png"))
            else:
                mp4 = local_gpu_dir / f"{sid:02d}_{slug}.mp4"
                if mp4.exists():
                    results[sid] = mp4

    finally:
        # ── 7. Always terminate the pod ───────────────────────────────────────
        if pod_id:
            print(f"[renderer] Terminating pod {pod_id}...")
            mgr.terminate()

    return results
