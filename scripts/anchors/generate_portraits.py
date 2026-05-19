"""
Generate photorealistic portrait headshots for each news anchor using
Stable Diffusion (Realistic Vision or similar checkpoint).

Produces 4 candidates per anchor — review and keep your preferred one.
Saved to: data/anchors/portraits/{anchor_id}_candidate_{n}.png
Final pick saved as: data/anchors/portraits/{anchor_id}.png

Usage:
    # Generate all 12 anchors
    python scripts/anchors/generate_portraits.py

    # Generate specific anchors
    python scripts/anchors/generate_portraits.py --anchors marcus_webb dana_reyes

    # Pick a candidate as the final portrait
    python scripts/anchors/generate_portraits.py --pick marcus_webb 2

Requirements:
    pip install diffusers accelerate torch pillow
    GPU recommended (runs on CPU but slow — ~5 min/image on CPU)
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROSTER_PATH = Path("data/anchors/roster.json")
PORTRAITS_DIR = Path("data/anchors/portraits")

# Shared quality boosters appended to every prompt
QUALITY_SUFFIX = (
    ", 4k, ultra detailed, professional photography, canon eos r5, "
    "85mm portrait lens, shallow depth of field, broadcast quality"
)

# Shared negative prompt — keeps results clean and realistic
NEGATIVE_PROMPT = (
    "cartoon, anime, illustration, painting, sketch, ugly, deformed, "
    "blurry, low quality, watermark, text, extra fingers, bad anatomy, "
    "unrealistic, over-saturated, plastic skin, doll-like"
)


def load_roster() -> list[dict]:
    with open(ROSTER_PATH) as f:
        return json.load(f)


def generate_portraits(
    anchors: list[dict],
    candidates: int = 4,
    steps: int = 75,
    guidance: float = 7.5,
    seed_base: int = 42,
    width: int = 768,
    height: int = 768,
):
    """Generate candidate portraits for each anchor using Stable Diffusion."""
    try:
        import torch
        from diffusers import StableDiffusionPipeline
    except ImportError:
        print("Install: pip install diffusers accelerate torch")
        sys.exit(1)

    PORTRAITS_DIR.mkdir(parents=True, exist_ok=True)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if device == "cuda" else torch.float32
    if device == "cpu":
        print("WARNING: Running on CPU — each image takes ~5 min. GPU strongly recommended.")

    print(f"Loading Stable Diffusion on {device}...")
    pipe = StableDiffusionPipeline.from_pretrained(
        "SG161222/Realistic_Vision_V6.0_B1_noVAE",
        torch_dtype=dtype,
        safety_checker=None,
        requires_safety_checker=False,
    ).to(device)
    pipe.enable_attention_slicing()

    print(f"Settings: {width}x{height}, {steps} steps, guidance {guidance}, {candidates} candidates/anchor")

    for anchor in anchors:
        aid = anchor["id"]
        name = anchor["name"]
        prompt = anchor["portrait_prompt"] + QUALITY_SUFFIX

        print(f"\nGenerating {candidates} portraits for: {name}")
        print(f"  Prompt: {prompt[:80]}...")

        for i in range(candidates):
            out_path = PORTRAITS_DIR / f"{aid}_candidate_{i + 1}.png"
            if out_path.exists():
                print(f"  [skip] {out_path.name} already exists")
                continue

            generator = torch.Generator(device=device).manual_seed(seed_base + i * 100)
            result = pipe(
                prompt=prompt,
                negative_prompt=NEGATIVE_PROMPT,
                num_inference_steps=steps,
                guidance_scale=guidance,
                width=width,
                height=height,
                generator=generator,
            )
            img = result.images[0]
            img.save(out_path)
            print(f"  Saved: {out_path.name}")

        print(f"  Review candidates in: {PORTRAITS_DIR}/")
        print(f"  Pick with: python scripts/anchors/generate_portraits.py --pick {aid} <1-{candidates}>")


def pick_portrait(anchor_id: str, candidate_num: int):
    """Copy a candidate as the final portrait for an anchor."""
    src = PORTRAITS_DIR / f"{anchor_id}_candidate_{candidate_num}.png"
    dst = PORTRAITS_DIR / f"{anchor_id}.png"

    if not src.exists():
        print(f"Candidate not found: {src}")
        print(f"Run generate first: python scripts/anchors/generate_portraits.py --anchors {anchor_id}")
        sys.exit(1)

    shutil.copy2(src, dst)
    print(f"Portrait set: {dst}")
    print(f"Final portrait saved for anchor: {anchor_id}")


def list_status(roster: list[dict]):
    """Show portrait generation status for all anchors."""
    PORTRAITS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"\n{'Anchor':<20} {'Final':^8} {'Candidates':^12}")
    print("-" * 44)
    for anchor in roster:
        aid = anchor["id"]
        name = anchor["name"]
        final = "✓" if (PORTRAITS_DIR / f"{aid}.png").exists() else "—"
        cands = len(list(PORTRAITS_DIR.glob(f"{aid}_candidate_*.png")))
        print(f"{name:<20} {final:^8} {cands:^12}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate anchor portrait headshots")
    parser.add_argument("--anchors", nargs="+", metavar="ID",
                        help="Anchor IDs to generate (default: all)")
    parser.add_argument("--candidates", type=int, default=8,
                        help="Number of candidate images per anchor (default: 8)")
    parser.add_argument("--steps", type=int, default=75,
                        help="Diffusion steps (default: 75)")
    parser.add_argument("--guidance", type=float, default=7.5,
                        help="CFG guidance scale (default: 7.5)")
    parser.add_argument("--seed", type=int, default=42,
                        help="Base random seed (default: 42)")
    parser.add_argument("--width", type=int, default=768,
                        help="Image width in pixels (default: 768)")
    parser.add_argument("--height", type=int, default=768,
                        help="Image height in pixels (default: 768)")
    parser.add_argument("--pick", nargs=2, metavar=("ANCHOR_ID", "NUM"),
                        help="Pick candidate N as final portrait for anchor")
    parser.add_argument("--status", action="store_true",
                        help="Show generation status for all anchors")
    args = parser.parse_args()

    roster = load_roster()

    if args.status:
        list_status(roster)
        sys.exit(0)

    if args.pick:
        pick_portrait(args.pick[0], int(args.pick[1]))
        sys.exit(0)

    # Filter to requested anchors
    if args.anchors:
        ids = set(args.anchors)
        targets = [a for a in roster if a["id"] in ids]
        missing = ids - {a["id"] for a in targets}
        if missing:
            print(f"Unknown anchor IDs: {', '.join(missing)}")
            print(f"Valid IDs: {', '.join(a['id'] for a in roster)}")
            sys.exit(1)
    else:
        targets = roster

    generate_portraits(
        targets,
        candidates=args.candidates,
        steps=args.steps,
        guidance=args.guidance,
        seed_base=args.seed,
        width=args.width,
        height=args.height,
    )
