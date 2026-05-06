"""
Collect broadcast news training data from archive.org.

Downloads news clips, extracts captions (or transcribes with Whisper),
extracts anchor face frames, and produces training datasets for both
the LLM fine-tune and talking head fine-tune pipelines.

Usage:
    python scripts/training/collect_data.py \\
        --query "news anchor broadcast" \\
        --collections CSPAN KGO KQED \\
        --max-clips 50 \\
        --output data/training \\
        --whisper-model base

Outputs:
    data/training/clips/          -- downloaded video + audio
    data/training/anchor_frames/  -- extracted single-face frames
    data/training/llm_dataset.json       -- Alpaca-format LLM training data
    data/training/talking_head_manifest.json  -- manifest for talking head training
"""
from __future__ import annotations

import argparse
from pathlib import Path

from core.training.scraper import collect_dataset
from core.training.transcriber import transcribe_all
from core.training.preparer import build_llm_dataset, build_talking_head_dataset
from core.training.face_extractor import extract_all_anchors


def main():
    parser = argparse.ArgumentParser(description="Collect archive.org training data")
    parser.add_argument("--query", default="news anchor broadcast", help="Search query")
    parser.add_argument("--collections", nargs="+",
                        default=["CSPAN", "KGO", "KQED", "WETA"],
                        help="archive.org collections to search")
    parser.add_argument("--max-clips", type=int, default=50)
    parser.add_argument("--max-duration", type=int, default=7200,
                        help="Max clip duration in seconds (default 2h; TV episodes are full broadcasts)")
    parser.add_argument("--output", type=Path, default=Path("data/training"))
    parser.add_argument("--whisper-model", default="base",
                        choices=["tiny", "base", "small", "medium"],
                        help="Whisper model size for clips without captions")
    parser.add_argument("--skip-frames", action="store_true",
                        help="Skip face frame extraction")
    args = parser.parse_args()

    clips_dir    = args.output / "clips"
    frames_dir   = args.output / "anchor_frames"
    llm_out      = args.output / "llm_dataset.json"
    th_manifest  = args.output / "talking_head_manifest.json"

    # ── 1. Download clips ────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("STEP 1: Downloading clips from archive.org")
    print(f"{'='*60}")
    clips = collect_dataset(
        output_dir=clips_dir,
        query=args.query,
        collections=args.collections,
        max_clips=args.max_clips,
        max_duration_sec=args.max_duration,
    )
    if not clips:
        print("No clips downloaded. Check your query or internet connection.")
        return

    # ── 2. Transcribe ────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("STEP 2: Transcribing / loading captions")
    print(f"{'='*60}")
    transcripts = transcribe_all(clips, whisper_model=args.whisper_model)
    print(f"Transcribed {len(transcripts)} clips")

    # ── 3. Build LLM dataset ─────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("STEP 3: Building LLM fine-tune dataset")
    print(f"{'='*60}")
    n_llm = build_llm_dataset(transcripts, llm_out, format="alpaca")
    print(f"LLM examples: {n_llm}")

    # ── 4. Build talking head manifest ───────────────────────────────────────
    print(f"\n{'='*60}")
    print("STEP 4: Building talking head manifest")
    print(f"{'='*60}")
    n_th = build_talking_head_dataset(clips_dir, th_manifest)
    print(f"Talking head clips: {n_th}")

    # ── 5. Extract anchor face frames ────────────────────────────────────────
    if not args.skip_frames:
        print(f"\n{'='*60}")
        print("STEP 5: Extracting anchor face frames")
        print(f"{'='*60}")
        results = extract_all_anchors(th_manifest, frames_dir)
        total_frames = sum(len(v) for v in results.values())
        print(f"Total frames extracted: {total_frames}")

    print(f"\n{'='*60}")
    print("DATA COLLECTION COMPLETE")
    print(f"{'='*60}")
    print(f"  Clips:          {clips_dir}")
    print(f"  LLM dataset:    {llm_out}  ({n_llm} examples)")
    print(f"  TH manifest:    {th_manifest}  ({n_th} clips)")
    if not args.skip_frames:
        print(f"  Anchor frames:  {frames_dir}")
    print()
    print("Next steps:")
    print("  LLM training (needs GPU):")
    print(f"    python scripts/training/train_llm.py --dataset {llm_out} --output models/llm_finetune")
    print("  Talking head training (needs GPU):")
    print(f"    python scripts/training/train_talking_head.py --manifest {th_manifest} --frames-dir {frames_dir} --output models/talking_head_finetune")


if __name__ == "__main__":
    main()
