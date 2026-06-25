#!/usr/bin/env python3
"""
AngryACGuy production pipeline — scaffold.

Workflow:
  1. ideas.py generates episode concepts
  2. script.py writes the full episode script (Ollama)
  3. tts.py generates voice audio (ElevenLabs — to be wired in)
  4. video.py assembles the short (footage + audio + captions)
  5. upload.py posts to YouTube / social (to be wired in)

Usage:
  python -m shorts.angry_ac_guy.pipeline --episode episodes/batch_01.json --index 0
  python -m shorts.angry_ac_guy.pipeline --episode episodes/batch_01.json --dry-run
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from shared import ollama
from shorts.angry_ac_guy.ideas import EpisodeIdea

_SCRIPT_SYSTEM = """You are writing a script for AngryACGuy — an HVAC technician YouTube channel.

FORMAT:
[HOOK - 0:00-0:05]
(action note)
DIALOGUE: "..."

[INTRO RANT - 0:05-0:45]
...

[MAIN CONTENT]
...

[CLOSER / CTA]
...

VOICE: Direct, angry-but-expert, working class, occasionally funny.
Write exactly what he says. Include action notes in (parentheses).
Do NOT include timestamps beyond the section headers."""


def generate_script(episode: EpisodeIdea, model: str = ollama._DEFAULT_MODEL) -> str:
    prompt = (
        f"Write a full YouTube script for this AngryACGuy episode:\n\n"
        f"Title: {episode.title}\n"
        f"Hook: {episode.hook}\n"
        f"Topic: {episode.topic}\n"
        f"Rant angle: {episode.rant_angle}\n"
        f"Educational core: {episode.educational_core}\n"
        f"Visual gags: {', '.join(episode.visual_gags)}\n"
        f"CTA: {episode.cta}\n"
        f"Target length: {episode.duration_estimate}\n\n"
        f"Write the complete script."
    )
    return ollama.call(prompt, system=_SCRIPT_SYSTEM, model=model,
                       temperature=0.8, max_tokens=4000)


def run(episode: EpisodeIdea, out_dir: Path, dry_run: bool = False,
        model: str = ollama._DEFAULT_MODEL) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    result: dict = {"episode": episode.title, "steps": {}}

    # Step 1: Script
    script_path = out_dir / "script.txt"
    if dry_run:
        print(f"  [dry-run] Would write script → {script_path}")
        result["steps"]["script"] = "dry-run"
    elif not script_path.exists():
        print(f"  Writing script ...")
        script = generate_script(episode, model=model)
        script_path.write_text(script, encoding="utf-8")
        print(f"    {len(script.split())} words → {script_path}")
        result["steps"]["script"] = str(script_path)
    else:
        print(f"  Script exists, skipping")
        result["steps"]["script"] = str(script_path)

    # Step 2: TTS — placeholder
    audio_path = out_dir / "audio.mp3"
    print(f"  [TODO] TTS: wire in ElevenLabs → {audio_path}")
    result["steps"]["tts"] = "pending"

    # Step 3: Video — placeholder
    video_path = out_dir / "output.mp4"
    print(f"  [TODO] Video: wire in video assembly → {video_path}")
    result["steps"]["video"] = "pending"

    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="AngryACGuy episode pipeline")
    parser.add_argument("--episode", required=True, help="Path to episode ideas JSON")
    parser.add_argument("--index", type=int, default=0)
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--model", default=ollama._DEFAULT_MODEL)
    args = parser.parse_args()

    episodes_raw = json.loads(Path(args.episode).read_text())
    episodes = [EpisodeIdea(**e) for e in episodes_raw]
    targets = episodes if args.all else [episodes[args.index]]

    for ep in targets:
        ep_dir = Path(__file__).parent / "episodes" / f"ep{ep.episode_number:03d}"
        print(f"\nEpisode {ep.episode_number}: {ep.title}")
        run(ep, ep_dir, dry_run=args.dry_run, model=args.model)


if __name__ == "__main__":
    main()
