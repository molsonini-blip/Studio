"""
Render a 10-second test clip for any anchor:
  portrait → SadTalker lip-sync → lower-third overlay → output MP4

Requires: portrait image, ElevenLabs voice assigned, SadTalker installed.

Usage:
    python scripts/anchors/preview_anchor.py --anchor marcus_webb
    python scripts/anchors/preview_anchor.py --anchor dana_reyes --script "Good evening."
    python scripts/anchors/preview_anchor.py --all   # render all anchors with portrait+voice
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import requests

ROSTER_PATH   = Path("data/anchors/roster.json")
PORTRAITS_DIR = Path("data/anchors/portraits")
VOICES_DIR    = Path("data/anchors/voices")
PREVIEWS_DIR  = Path("data/anchors/previews")
ELEVENLABS_BASE = "https://api.elevenlabs.io/v1"

DEFAULT_SCRIPTS = {
    "marcus_webb":    "Good evening. I'm Marcus Webb. Here are tonight's top stories.",
    "dana_reyes":     "Good morning. I'm Dana Reyes, and we have a lot to cover today.",
    "james_callahan": "Good evening, everyone. James Callahan here. Let's get right to it.",
    "priya_nair":     "Good afternoon. I'm Priya Nair. Here is what you need to know.",
    "mei_lin_zhou":   "Good evening. I'm Mei-Lin Zhou. Tonight's headlines, straight ahead.",
    "tyler_brooks":   "Hey, I'm Tyler Brooks. Here's what's trending in the news today.",
    "sofia_okafor":   "Hi everyone, Sofia Okafor here. Let's break down today's stories.",
    "carlos_mendez":  "Good evening. Carlos Mendez with you tonight. Here are the stories that matter.",
    "aisha_thompson": "I'm Aisha Thompson. Breaking news tonight — here's what we know.",
    "kevin_park":     "Good evening. I'm Kevin Park. Tonight we're looking at the numbers.",
    "rachel_torres":  "Hey! Rachel Torres here. Here's what everyone is talking about today.",
    "layla_hassan":   "Good evening. I'm Layla Hassan. Tonight's top stories from around the world.",
}


def load_roster() -> list[dict]:
    with open(ROSTER_PATH) as f:
        return json.load(f)


def _tts(anchor: dict, script: str, out_path: Path, api_key: str) -> bool:
    """Generate TTS audio via ElevenLabs. Returns True on success."""
    voice_id = anchor.get("elevenlabs_voice_id")
    if not voice_id:
        print(f"  [skip] No voice_id for {anchor['name']}. Run setup_voices.py first.")
        return False

    resp = requests.post(
        f"{ELEVENLABS_BASE}/text-to-speech/{voice_id}",
        headers={"xi-api-key": api_key, "Accept": "audio/mpeg", "Content-Type": "application/json"},
        json={
            "text": script,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
        },
        timeout=60,
    )
    if resp.status_code != 200:
        print(f"  [tts error] {resp.status_code}: {resp.text[:200]}")
        return False

    out_path.write_bytes(resp.content)
    return True


def _sadtalker(portrait: Path, audio: Path, out_path: Path) -> bool:
    """Run SadTalker inference to produce lip-synced video."""
    sadtalker_dir = Path("models/sadtalker")
    if not sadtalker_dir.exists():
        print("  [skip] SadTalker not found. Run scripts/download_models.py --sadtalker")
        return False

    cmd = [
        sys.executable,
        str(sadtalker_dir / "inference.py"),
        "--driven_audio", str(audio),
        "--source_image", str(portrait),
        "--result_dir", str(out_path.parent),
        "--still",
        "--enhancer", "gfpgan",
        "--preprocess", "crop",
    ]
    try:
        subprocess.run(cmd, check=True, timeout=300)
        # SadTalker names output based on input filenames — find it
        candidates = list(out_path.parent.glob("*.mp4"))
        if candidates:
            candidates[0].rename(out_path)
            return True
        print("  [sadtalker] No output MP4 found")
        return False
    except Exception as e:
        print(f"  [sadtalker error] {e}")
        return False


def _add_lower_third(video_path: Path, anchor: dict, out_path: Path) -> bool:
    """Burn a lower-third name/title graphic onto the video using ffmpeg."""
    lt = anchor["lower_third"]
    name  = lt["name"]
    title = lt["title"]
    color = lt["color_accent"].lstrip("#")

    # ffmpeg drawbox + drawtext for a simple broadcast lower-third
    filter_complex = (
        f"drawbox=x=0:y=ih-80:w=iw:h=80:color=0x{color}@0.85:t=fill,"
        f"drawtext=text='{name}':fontcolor=white:fontsize=28:x=20:y=h-65:fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf,"
        f"drawtext=text='{title}':fontcolor=white@0.85:fontsize=18:x=20:y=h-35:fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    )

    try:
        subprocess.run([
            "ffmpeg", "-i", str(video_path),
            "-vf", filter_complex,
            "-c:a", "copy",
            str(out_path), "-y", "-loglevel", "error"
        ], check=True, timeout=120)
        return True
    except Exception as e:
        print(f"  [lower-third error] {e} — saving without overlay")
        import shutil
        shutil.copy2(video_path, out_path)
        return False


def render_preview(anchor: dict, script: str, api_key: str) -> Path | None:
    aid = anchor["id"]
    name = anchor["name"]

    portrait = PORTRAITS_DIR / f"{aid}.png"
    if not portrait.exists():
        print(f"  [skip] No final portrait for {name}.")
        print(f"         Run: python scripts/anchors/generate_portraits.py --anchors {aid}")
        print(f"         Then: python scripts/anchors/generate_portraits.py --pick {aid} <1-4>")
        return None

    PREVIEWS_DIR.mkdir(parents=True, exist_ok=True)
    final_out = PREVIEWS_DIR / f"{aid}_preview.mp4"

    print(f"\nRendering preview: {name}")
    print(f"  Script: \"{script}\"")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        audio_path = tmp_path / f"{aid}.mp3"
        raw_video  = tmp_path / f"{aid}_raw.mp4"

        # 1. TTS
        print("  [1/3] Generating voice...")
        if not _tts(anchor, script, audio_path, api_key):
            return None

        # 2. SadTalker lip-sync
        print("  [2/3] Animating portrait...")
        if not _sadtalker(portrait, audio_path, raw_video):
            return None

        # 3. Lower-third overlay
        print("  [3/3] Adding lower-third...")
        _add_lower_third(raw_video, anchor, final_out)

    print(f"  Preview saved: {final_out}")
    return final_out


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Render test clips for news anchors")
    parser.add_argument("--anchor", metavar="ID", help="Anchor ID to render")
    parser.add_argument("--all", action="store_true", help="Render all ready anchors")
    parser.add_argument("--script", default="", help="Custom intro script")
    parser.add_argument("--status", action="store_true", help="Show readiness for all anchors")
    args = parser.parse_args()

    roster = load_roster()

    if args.status:
        print(f"\n{'Anchor':<20} {'Portrait':^10} {'Voice':^10} {'Preview':^10}")
        print("-" * 54)
        for a in roster:
            has_portrait = (PORTRAITS_DIR / f"{a['id']}.png").exists()
            has_voice    = bool(a.get("elevenlabs_voice_id"))
            has_preview  = (PREVIEWS_DIR / f"{a['id']}_preview.mp4").exists()
            print(
                f"{a['name']:<20} "
                f"{'✓' if has_portrait else '—':^10} "
                f"{'✓' if has_voice else '—':^10} "
                f"{'✓' if has_preview else '—':^10}"
            )
        sys.exit(0)

    api_key = os.environ.get("ELEVENLABS_API_KEY", "")
    if not api_key:
        print("ERROR: ELEVENLABS_API_KEY not set.")
        sys.exit(1)

    if args.all:
        for anchor in roster:
            script = DEFAULT_SCRIPTS.get(anchor["id"], f"Hello, I'm {anchor['name']}.")
            render_preview(anchor, script, api_key)
    elif args.anchor:
        anchor = next((a for a in roster if a["id"] == args.anchor), None)
        if not anchor:
            print(f"Unknown anchor ID: {args.anchor}")
            print(f"Valid: {', '.join(a['id'] for a in roster)}")
            sys.exit(1)
        script = args.script or DEFAULT_SCRIPTS.get(anchor["id"], f"Hello, I'm {anchor['name']}.")
        render_preview(anchor, script, api_key)
    else:
        parser.print_help()
