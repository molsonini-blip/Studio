#!/usr/bin/env python3
"""
One-command Studio broadcast producer.

Usage:
  python scripts/produce.py                        # full pipeline
  python scripts/produce.py --anchors 3            # 3 anchors (default)
  python scripts/produce.py --gpu "RTX A4000"      # different GPU type
  python scripts/produce.py --dry-run              # fetch+TTS only, no GPU

Required env vars:
  ELEVENLABS_API_KEY   ElevenLabs TTS
  RUNPOD_API_KEY       RunPod pod lifecycle

Set them in .env or export before running:
  export ELEVENLABS_API_KEY=your_key
  export RUNPOD_API_KEY=your_key
  python scripts/produce.py
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

# Allow imports from project root
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Load .env if present
_env_file = Path(__file__).resolve().parents[1] / ".env"
if _env_file.exists():
    for line in _env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


def main() -> None:
    parser = argparse.ArgumentParser(description="Studio AI broadcast producer")
    parser.add_argument("--anchors", type=int, default=3, help="Number of anchors per episode")
    parser.add_argument("--endpoint", default=None, help="RunPod Serverless endpoint ID (overrides RUNPOD_ENDPOINT_ID env var)")
    parser.add_argument("--dry-run", action="store_true", help="Fetch + TTS only, skip GPU render")
    args = parser.parse_args()

    missing = []
    if not args.dry_run and not os.environ.get("ELEVENLABS_API_KEY"):
        missing.append("ELEVENLABS_API_KEY")
    if not args.dry_run and not os.environ.get("RUNPOD_API_KEY"):
        missing.append("RUNPOD_API_KEY")
    if missing:
        print(f"ERROR: Missing env vars: {', '.join(missing)}")
        print("Set them in .env or export before running.")
        sys.exit(1)

    from core.production.pipeline import run

    t0 = time.time()
    output = run(
        anchors_per_episode=args.anchors,
        runpod_api_key=os.environ.get("RUNPOD_API_KEY"),
        endpoint_id=args.endpoint,
        dry_run=args.dry_run,
    )
    elapsed = time.time() - t0

    if output:
        print(f"\nDone in {elapsed:.0f}s  ->  {output}")
    else:
        print(f"\nDone in {elapsed:.0f}s (dry run)")


if __name__ == "__main__":
    main()
