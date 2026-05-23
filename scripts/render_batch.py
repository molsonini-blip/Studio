#!/usr/bin/env python3
"""
Runs ON the RunPod pod. Receives a job JSON file and renders each segment
via SadTalker. Called remotely by pipeline.py over SSH.

Usage:
  python3 scripts/render_batch.py --job /workspace/studio/render_job.json

Job JSON format:
  {
    "segments": [
      {
        "anchor_id": "marcus_webb",
        "audio": "/workspace/studio/tmp/marcus_webb.mp3",
        "portrait": "/workspace/studio/data/anchors/portraits/marcus_webb.png",
        "output": "/workspace/studio/outputs/marcus_webb_seg.mp4"
      },
      ...
    ],
    "sadtalker_dir": "/workspace/studio/models/sadtalker"
  }
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def render_segment(
    audio: Path,
    portrait: Path,
    output: Path,
    sadtalker_dir: Path,
) -> None:
    out_dir = output.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable,
        "inference.py",
        "--driven_audio", str(audio.resolve()),
        "--source_image", str(portrait.resolve()),
        "--result_dir", str(out_dir.resolve()),
        "--still",
        "--preprocess", "crop",
    ]

    before = set(out_dir.rglob("*.mp4"))
    subprocess.run(cmd, check=True, timeout=600, cwd=str(sadtalker_dir.resolve()))
    after = set(out_dir.rglob("*.mp4"))

    new_files = sorted(after - before, key=lambda p: p.stat().st_mtime, reverse=True)
    if not new_files:
        raise RuntimeError(f"SadTalker produced no MP4 for {audio.name}")

    new_files[0].rename(output)
    print(f"  -> {output}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--job", required=True, help="Path to render_job.json")
    args = parser.parse_args()

    job = json.loads(Path(args.job).read_text())
    sadtalker_dir = Path(job["sadtalker_dir"])
    segments = job["segments"]

    print(f"[render_batch] {len(segments)} segments to render")
    for i, seg in enumerate(segments):
        anchor_id = seg["anchor_id"]
        print(f"[render_batch] [{i+1}/{len(segments)}] {anchor_id}")
        render_segment(
            audio=Path(seg["audio"]),
            portrait=Path(seg["portrait"]),
            output=Path(seg["output"]),
            sadtalker_dir=sadtalker_dir,
        )

    print("[render_batch] All segments done.")


if __name__ == "__main__":
    main()
