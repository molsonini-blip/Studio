#!/usr/bin/env python3
"""
Jim Hall Movie — full production pipeline.

Reads the 24-scene screenplay, refines narration via Ollama, generates
ElevenLabs TTS audio, and optionally renders FLUX images or CogVideoX video
clips on RunPod GPU.

Usage:
  # Full narration pipeline (on the server):
  python scripts/jim_hall_movie.py

  # Skip Ollama refinement:
  python scripts/jim_hall_movie.py --skip-ollama

  # Dry run — scripts only, no TTS:
  python scripts/jim_hall_movie.py --dry-run

  # Single scene:
  python scripts/jim_hall_movie.py --scene 12

  # Re-generate audio even if it already exists:
  python scripts/jim_hall_movie.py --retry

  # Generate FLUX images on RunPod GPU (HIGH/HIGHEST priority scenes):
  python scripts/jim_hall_movie.py --render-images

  # Generate CogVideoX video clips on RunPod GPU:
  python scripts/jim_hall_movie.py --render-video

  # Generate all scenes' images (not just priority):
  python scripts/jim_hall_movie.py --render-images --all-scenes

  # Images per scene (default 3):
  python scripts/jim_hall_movie.py --render-images --images-per-scene 5

Run on the server (won't be interrupted):
  nohup python scripts/jim_hall_movie.py --skip-ollama > /opt/studio/outputs/jim_hall/run.log 2>&1 &
  tail -f /opt/studio/outputs/jim_hall/run.log
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

# Allow imports from project root
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Load .env
_env_file = Path(__file__).resolve().parents[1] / ".env"
if _env_file.exists():
    for line in _env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Jim Hall Movie — narration producer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--skip-ollama", action="store_true",
                        help="Use raw VO text without Ollama refinement")
    parser.add_argument("--dry-run", action="store_true",
                        help="Write scripts only, no TTS audio")
    parser.add_argument("--scene", type=int, default=None,
                        help="Process only this scene ID (1-24)")
    parser.add_argument("--retry", action="store_true",
                        help="Re-generate audio even if it already exists")
    parser.add_argument("--output", type=str, default=None,
                        help="Override output directory (default: outputs/jim_hall)")
    # GPU render flags
    parser.add_argument("--render-images", action="store_true",
                        help="Generate FLUX images on RunPod GPU after TTS")
    parser.add_argument("--render-video", action="store_true",
                        help="Generate CogVideoX video clips on RunPod GPU after TTS")
    parser.add_argument("--gpu-only", action="store_true",
                        help="Skip TTS, go straight to GPU render (use if audio already done)")
    parser.add_argument("--all-scenes", action="store_true",
                        help="GPU render all scenes (default: HIGH/HIGHEST priority only)")
    parser.add_argument("--images-per-scene", type=int, default=3,
                        help="Number of FLUX images to generate per scene (default: 3)")
    parser.add_argument("--gpu-wait-hours", type=float, default=2.0,
                        help="How many hours to keep retrying if GPU pods are sold out (default: 2)")
    args = parser.parse_args()

    api_key = os.environ.get("ELEVENLABS_API_KEY")
    runpod_key = os.environ.get("RUNPOD_API_KEY")

    if not api_key and not args.dry_run and not args.gpu_only:
        print("ERROR: ELEVENLABS_API_KEY not set. Add to .env or export before running.")
        sys.exit(1)

    if (args.render_images or args.render_video) and not runpod_key:
        print("ERROR: RUNPOD_API_KEY not set. Required for GPU rendering.")
        sys.exit(1)

    from core.movie.scenes import SCENES
    from core.movie.narrator import refine_all_scenes
    from core.movie.producer import produce_movie

    # Determine output root
    project_root = Path(__file__).resolve().parents[1]
    output_root = Path(args.output) if args.output else project_root / "outputs" / "jim_hall"
    output_root.mkdir(parents=True, exist_ok=True)

    # Filter scenes
    scenes = SCENES
    if args.scene is not None:
        scenes = [s for s in scenes if s["id"] == args.scene]
        if not scenes:
            print(f"ERROR: Scene {args.scene} not found (valid: 1-24)")
            sys.exit(1)

    total = len(scenes)
    print(f"\n{'='*60}")
    print(f"  Jim Hall Movie — Narration Producer")
    print(f"{'='*60}")
    print(f"  Scenes:      {total}")
    print(f"  Ollama:      {'SKIP' if args.skip_ollama else 'ON'}")
    print(f"  TTS:         {'SKIP (--gpu-only)' if args.gpu_only else 'DRY RUN' if args.dry_run else 'ON (ElevenLabs)'}")
    print(f"  GPU images:  {'ON (RunPod FLUX)' if args.render_images else 'OFF'}")
    print(f"  GPU video:   {'ON (RunPod CogVideoX)' if args.render_video else 'OFF'}")
    print(f"  Output:      {output_root}")
    print(f"{'='*60}\n")

    t0 = time.time()

    if not args.gpu_only:
        # Step 1: Refine narration through Ollama
        print("[1/3] Refining narration scripts...")
        refined_scenes = refine_all_scenes(scenes, skip_ollama=args.skip_ollama)
        print(f"  Done — {len(refined_scenes)} scenes refined\n")

        # Step 2: Generate TTS and write outputs
        print("[2/3] Generating TTS audio and saving outputs...")
        manifest_path = produce_movie(
            scenes=refined_scenes,
            output_root=output_root,
            api_key=api_key or "",
            dry_run=args.dry_run,
            retry_existing=args.retry,
        )
    else:
        refined_scenes = scenes
        manifest_path = output_root / "manifest.json"
        print("[skip] TTS skipped (--gpu-only)\n")

    # Step 3: GPU render (optional)
    if args.render_images or args.render_video:
        from core.movie.renderer import render_images, render_video
        priority_only = not args.all_scenes

        if args.render_images:
            print(f"\n[3/3] GPU: Generating FLUX images on RunPod...")
            print(f"  Will retry for up to {args.gpu_wait_hours}h if GPU market is sold out")
            img_results = render_images(
                refined_scenes,
                output_root,
                api_key=runpod_key,
                images_per_scene=args.images_per_scene,
                priority_only=priority_only,
                max_wait_minutes=int(args.gpu_wait_hours * 60),
            )
            print(f"  Images generated for {len(img_results)} scenes")

        if args.render_video:
            print(f"\n[3/3] GPU: Generating CogVideoX video on RunPod...")
            vid_results = render_video(
                refined_scenes,
                output_root,
                api_key=runpod_key,
                priority_only=priority_only,
            )
            print(f"  Video clips generated for {len(vid_results)} scenes")
    else:
        print("[3/3] GPU render: OFF (use --render-images or --render-video to enable)")

    elapsed = time.time() - t0
    print(f"\n{'='*60}")
    print(f"  Done in {elapsed:.0f}s")
    if manifest_path.exists():
        print(f"  Manifest:    {manifest_path}")
    print(f"  Audio:       {output_root / 'audio'}")
    print(f"  Scripts:     {output_root / 'scripts'}")
    if args.render_images:
        print(f"  Images:      {output_root / 'gpu_images'}")
    if args.render_video:
        print(f"  Video:       {output_root / 'gpu_video'}")
    print(f"{'='*60}\n")

    # Print summary
    import json
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        audio_count = sum(1 for s in manifest if s.get("audio_path"))
        total_chars = sum(s.get("vo_chars", 0) for s in manifest)
        print(f"  Audio files generated: {audio_count}/{len(manifest)}")
        print(f"  Total narration chars: {total_chars:,}")
        if total_chars:
            print(f"  ElevenLabs chars used: {total_chars:,} "
                  f"(~{total_chars/100000*100:.1f}% of 100K/month plan)")


if __name__ == "__main__":
    main()
