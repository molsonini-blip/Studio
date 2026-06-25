#!/usr/bin/env python3
"""
Jim Hall Movie — GPU render script (runs ON a RunPod pod).

This script is uploaded to the pod by renderer.py and executed there.
It reads a job JSON file and generates:
  - FLUX.1-schnell images for each scene (mode=images)
  - CogVideoX-5B video clips for each scene (mode=video)

Do NOT run this locally — it requires a CUDA GPU with 16-24GB VRAM.

Usage (on pod):
  python jim_hall_render_gpu.py --job /workspace/studio/jim_hall_job.json --output /workspace/outputs
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path


# ── Image generation with FLUX.1-schnell ──────────────────────────────────────

def render_images(jobs: list[dict], output_dir: Path, images_per_scene: int = 3) -> None:
    import torch
    from diffusers import FluxPipeline

    print(f"[gpu] Loading FLUX.1-schnell (requires ~12GB VRAM)...")
    t0 = time.time()
    pipe = FluxPipeline.from_pretrained(
        "black-forest-labs/FLUX.1-schnell",
        torch_dtype=torch.bfloat16,
    )
    pipe = pipe.to("cuda")
    # Enable memory-efficient attention
    try:
        pipe.enable_xformers_memory_efficient_attention()
    except Exception:
        pass
    print(f"[gpu] FLUX loaded in {time.time()-t0:.1f}s")

    for job in jobs:
        sid = job["id"]
        slug = job["slug"]
        prompts = job.get("image_prompts", [])

        if not prompts:
            print(f"[gpu] Scene {sid} {slug}: no image prompts, skipping")
            continue

        scene_dir = output_dir / f"{sid:02d}_{slug}"
        scene_dir.mkdir(parents=True, exist_ok=True)

        # Generate images_per_scene images using the available prompts
        for i in range(images_per_scene):
            prompt = prompts[i % len(prompts)]
            out_path = scene_dir / f"img_{i+1:02d}.png"

            if out_path.exists():
                print(f"  [skip] {out_path.name} exists")
                continue

            print(f"  [flux] Scene {sid} image {i+1}/{images_per_scene}: {prompt[:80]}...")
            t_img = time.time()
            try:
                result = pipe(
                    prompt=prompt,
                    num_inference_steps=4,         # schnell is optimized for 4 steps
                    guidance_scale=0.0,            # schnell uses cfg=0
                    height=768,
                    width=1360,                    # 2.39:1 cinemascope ratio
                    max_sequence_length=256,
                )
                result.images[0].save(str(out_path))
                print(f"    saved {out_path.name} in {time.time()-t_img:.1f}s")
            except Exception as e:
                print(f"    ERROR: {e}")

    print(f"[gpu] Image generation complete")


# ── Video generation with CogVideoX-5B ────────────────────────────────────────

def render_video(jobs: list[dict], output_dir: Path) -> None:
    import torch
    from diffusers import CogVideoXPipeline
    from diffusers.utils import export_to_video

    print(f"[gpu] Loading CogVideoX-5B (requires ~16GB VRAM)...")
    t0 = time.time()
    pipe = CogVideoXPipeline.from_pretrained(
        "THUDM/CogVideoX-5b",
        torch_dtype=torch.bfloat16,
    )
    pipe = pipe.to("cuda")
    pipe.enable_model_cpu_offload()
    pipe.vae.enable_slicing()
    pipe.vae.enable_tiling()
    print(f"[gpu] CogVideoX loaded in {time.time()-t0:.1f}s")

    for job in jobs:
        sid = job["id"]
        slug = job["slug"]
        prompt = job.get("video_prompt", "")
        negative = job.get("video_negative", "")

        if not prompt:
            print(f"[gpu] Scene {sid} {slug}: no video prompt, skipping")
            continue

        out_path = output_dir / f"{sid:02d}_{slug}.mp4"

        if out_path.exists() and out_path.stat().st_size > 10000:
            print(f"  [skip] {out_path.name} exists")
            continue

        print(f"  [cogvideo] Scene {sid}: {prompt[:80]}...")
        t_vid = time.time()
        try:
            result = pipe(
                prompt=prompt,
                negative_prompt=negative or "blurry, low quality, text, watermark, logo, modern, CGI, digital artifacts",
                num_frames=49,          # ~6 seconds at 8fps
                num_inference_steps=50,
                guidance_scale=6.0,
                use_dynamic_cfg=True,
                generator=torch.Generator("cuda").manual_seed(sid * 42),
            )
            frames = result.frames[0]
            export_to_video(frames, str(out_path), fps=8)
            size_mb = out_path.stat().st_size / 1024 / 1024
            print(f"    saved {out_path.name} ({size_mb:.1f}MB) in {time.time()-t_vid:.1f}s")
        except Exception as e:
            print(f"    ERROR: {e}")

    print(f"[gpu] Video generation complete")


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--job", required=True, help="Path to job JSON file")
    parser.add_argument("--output", required=True, help="Output directory")
    args = parser.parse_args()

    job_data = json.loads(Path(args.job).read_text())
    mode = job_data.get("mode", "images")
    jobs = job_data.get("jobs", [])
    images_per_scene = job_data.get("images_per_scene", 3)

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"  Jim Hall Movie — GPU Render")
    print(f"{'='*60}")
    print(f"  Mode:    {mode}")
    print(f"  Scenes:  {len(jobs)}")
    print(f"  Output:  {output_dir}")

    # Check GPU
    try:
        import torch
        if torch.cuda.is_available():
            name = torch.cuda.get_device_name(0)
            vram = torch.cuda.get_device_properties(0).total_memory / 1024**3
            print(f"  GPU:     {name} ({vram:.1f}GB VRAM)")
        else:
            print("  WARNING: No CUDA GPU — will be extremely slow")
    except ImportError:
        print("  WARNING: torch not available")

    print(f"{'='*60}\n")

    t0 = time.time()
    if mode == "images":
        render_images(jobs, output_dir, images_per_scene)
    elif mode == "video":
        render_video(jobs, output_dir)
    else:
        print(f"ERROR: Unknown mode '{mode}'. Use 'images' or 'video'.")
        sys.exit(1)

    elapsed = time.time() - t0
    print(f"\n[gpu] Total time: {elapsed/60:.1f} min")
    print(f"[gpu] Outputs in: {output_dir}")

    # List outputs
    files = list(output_dir.rglob("*.png")) + list(output_dir.rglob("*.mp4"))
    print(f"[gpu] Files generated: {len(files)}")
    for f in sorted(files)[:20]:
        print(f"  {f.relative_to(output_dir)}")


if __name__ == "__main__":
    main()
