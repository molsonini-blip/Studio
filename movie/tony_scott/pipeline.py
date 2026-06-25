#!/usr/bin/env python3
"""
Tony Scott documentary — full production pipeline.

Workflow:
  1. narrator.py generates + refines VO for all 13 scenes
  2. ElevenLabs generates TTS audio for each scene's VO
  3. (Manual) Archival footage and interview clips assembled per scene
  4. Final assembly: VO audio + footage → finished scenes

Usage:
  # Generate all narration scripts:
  python -m movie.tony_scott.pipeline --narration

  # Generate TTS audio for all scenes:
  python -m movie.tony_scott.pipeline --tts

  # Single scene:
  python -m movie.tony_scott.pipeline --scene 5 --narration --tts

  # Full pipeline (narration + TTS):
  python -m movie.tony_scott.pipeline --all

  # Dry run:
  python -m movie.tony_scott.pipeline --all --dry-run
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from movie.tony_scott.scenes import SCENES, get_scene
from movie.tony_scott.narrator import generate_vo, refine
from shared import budget

OUTPUT_DIR = Path(__file__).parent / "output"
VO_CACHE = Path(__file__).parent / "vo_scripts.json"

# Narrator voice — use a Marcus Webb-style voice or a dedicated documentary narrator voice
# Set TONY_SCOTT_NARRATOR_VOICE_ID in env, or use this default
NARRATOR_VOICE_ID = os.environ.get("TONY_SCOTT_NARRATOR_VOICE_ID", "pNInz6obpgDQGcFmaJgB")


def ensure_vo(scene_number: int | None = None, dry_run: bool = False) -> dict[int, str]:
    """Load or generate VO scripts. Returns {scene_number: refined_vo}."""
    cache: dict[int, dict] = {}
    if VO_CACHE.exists():
        for item in json.loads(VO_CACHE.read_text()):
            cache[item["number"]] = item

    scenes = [get_scene(scene_number)] if scene_number else SCENES
    results = {}

    for scene in scenes:
        if not scene:
            continue
        if scene.number in cache and cache[scene.number].get("refined_vo"):
            print(f"  Scene {scene.number}: VO cached")
            results[scene.number] = cache[scene.number]["refined_vo"]
            continue

        if dry_run:
            print(f"  Scene {scene.number}: [dry-run] Would generate VO")
            results[scene.number] = f"[DRY RUN] VO for scene {scene.number}: {scene.title}"
            continue

        print(f"  Scene {scene.number}: Generating VO ...")
        raw = generate_vo(scene)
        refined = refine(scene, raw)
        cache[scene.number] = {
            "number": scene.number,
            "title": scene.title,
            "act": scene.act,
            "raw_vo": raw,
            "refined_vo": refined,
        }
        results[scene.number] = refined
        print(f"    {len(refined.split())} words")

    # Save updated cache
    if not dry_run:
        VO_CACHE.write_text(json.dumps(list(cache.values()), indent=2))

    return results


def generate_tts(vo_scripts: dict[int, str], dry_run: bool = False) -> dict[int, Path]:
    """Generate ElevenLabs TTS audio for each scene's VO."""
    try:
        import httpx
    except ImportError:
        print("Install httpx: pip install httpx")
        sys.exit(1)

    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key and not dry_run:
        raise RuntimeError("Set ELEVENLABS_API_KEY env var")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    audio_paths: dict[int, Path] = {}

    for scene_num, vo_text in sorted(vo_scripts.items()):
        out_path = OUTPUT_DIR / f"scene_{scene_num:02d}_vo.mp3"

        if out_path.exists():
            print(f"  Scene {scene_num}: audio exists, skipping")
            audio_paths[scene_num] = out_path
            continue

        if dry_run:
            print(f"  Scene {scene_num}: [dry-run] Would generate TTS → {out_path}")
            audio_paths[scene_num] = out_path
            continue

        char_count = len(vo_text)
        est_cost = budget.estimate_elevenlabs(char_count)
        if not budget.charge("elevenlabs", est_cost, f"tony_scott_scene_{scene_num}"):
            print(f"  Scene {scene_num}: ElevenLabs budget exceeded, stopping")
            break

        print(f"  Scene {scene_num}: TTS ({char_count} chars) ...")
        resp = httpx.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{NARRATOR_VOICE_ID}",
            headers={"xi-api-key": api_key},
            json={
                "text": vo_text,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {"stability": 0.6, "similarity_boost": 0.8},
            },
            timeout=120,
        )
        resp.raise_for_status()
        out_path.write_bytes(resp.content)
        print(f"    Saved: {out_path}")
        audio_paths[scene_num] = out_path

    return audio_paths


def main() -> None:
    parser = argparse.ArgumentParser(description="Tony Scott documentary pipeline")
    parser.add_argument("--scene", type=int, default=0,
                        help="Process a single scene (0 = all)")
    parser.add_argument("--narration", action="store_true",
                        help="Generate/refresh narration scripts")
    parser.add_argument("--tts", action="store_true",
                        help="Generate TTS audio")
    parser.add_argument("--all", action="store_true",
                        help="Run full pipeline: narration + TTS")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--status", action="store_true",
                        help="Show what has been generated so far")
    args = parser.parse_args()

    if args.status:
        print(f"\nTony Scott Documentary Status")
        print(f"  VO Cache: {'exists' if VO_CACHE.exists() else 'not generated'}")
        if VO_CACHE.exists():
            cached = json.loads(VO_CACHE.read_text())
            print(f"  Scenes with VO: {len(cached)}/{len(SCENES)}")
        print(f"  TTS Audio Files:")
        for s in SCENES:
            p = OUTPUT_DIR / f"scene_{s.number:02d}_vo.mp3"
            status = "done" if p.exists() else "pending"
            print(f"    Scene {s.number:2d} {s.title[:30]:30} [{status}]")
        return

    do_narration = args.narration or args.all
    do_tts = args.tts or args.all
    scene_num = args.scene or None

    if do_narration:
        print(f"\nGenerating narration{'  (dry-run)' if args.dry_run else ''} ...")
        vo_scripts = ensure_vo(scene_num, dry_run=args.dry_run)
        print(f"  {len(vo_scripts)} scenes ready")
    elif do_tts:
        # Load from cache
        if not VO_CACHE.exists():
            print("No VO cache found. Run --narration first.")
            sys.exit(1)
        items = json.loads(VO_CACHE.read_text())
        vo_scripts = {i["number"]: i["refined_vo"] for i in items}
        if scene_num:
            vo_scripts = {k: v for k, v in vo_scripts.items() if k == scene_num}
    else:
        parser.print_help()
        return

    if do_tts:
        print(f"\nGenerating TTS audio{'  (dry-run)' if args.dry_run else ''} ...")
        audio = generate_tts(vo_scripts, dry_run=args.dry_run)
        print(f"  {len(audio)} audio files ready")

    budget.print_status()


if __name__ == "__main__":
    main()
