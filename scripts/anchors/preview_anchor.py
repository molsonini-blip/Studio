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


def _static_video(portrait: Path, audio: Path, out_path: Path) -> bool:
    """CPU-only: combine portrait + audio with a subtle Ken Burns zoom into a video."""
    try:
        # Get audio duration
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(audio)],
            capture_output=True, text=True, timeout=30,
        )
        duration = float(probe.stdout.strip()) if probe.stdout.strip() else 10.0

        # Slow zoom: scale from 100% to 105% over the clip duration
        zoom_filter = (
            f"zoompan=z='min(zoom+0.0003,1.05)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            f":d={int(duration * 25)}:s=768x768:fps=25"
        )
        subprocess.run([
            "ffmpeg",
            "-loop", "1", "-i", str(portrait),
            "-i", str(audio),
            "-vf", zoom_filter,
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k",
            "-t", str(duration),
            "-shortest",
            str(out_path), "-y", "-loglevel", "error",
        ], check=True, timeout=300)
        return True
    except Exception as e:
        print(f"  [static error] {e}")
        return False


def _sadtalker(portrait: Path, audio: Path, out_path: Path) -> bool:
    """Run SadTalker inference to produce lip-synced video."""
    sadtalker_dir = Path("models/sadtalker")
    if not sadtalker_dir.exists():
        print("  [skip] SadTalker not found. Run scripts/download_models.py --sadtalker")
        return False

    cmd = [
        sys.executable,
        "inference.py",
        "--driven_audio", str(audio.resolve()),
        "--source_image", str(portrait.resolve()),
        "--result_dir", str(out_path.parent.resolve()),
        "--still",
        "--preprocess", "crop",
    ]
    try:
        before = set(out_path.parent.rglob("*.mp4"))
        subprocess.run(cmd, check=True, timeout=600, cwd=str(sadtalker_dir.resolve()))
        after = set(out_path.parent.rglob("*.mp4"))
        new_files = sorted(after - before, key=lambda p: p.stat().st_mtime, reverse=True)
        if new_files:
            new_files[0].rename(out_path)
            return True
        print("  [sadtalker] No output MP4 found")
        return False
    except Exception as e:
        print(f"  [sadtalker error] {e}")
        return False


_FONT_CANDIDATES = [
    # Debian/Ubuntu
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    # RHEL/CentOS
    "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans.ttf",
    # macOS
    "/System/Library/Fonts/Helvetica.ttc",
    # Windows
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/arial.ttf",
]


def _find_fonts() -> tuple[str, str]:
    """Return (bold_font, regular_font) fontfile args, or empty strings if none found."""
    bold = next((f for f in _FONT_CANDIDATES if Path(f).exists() and "Bold" in f or "bd" in f), "")
    regular = next((f for f in _FONT_CANDIDATES if Path(f).exists() and "Bold" not in f and "bd" not in f), "")
    if not bold:
        bold = next((f for f in _FONT_CANDIDATES if Path(f).exists()), "")
    if not regular:
        regular = bold
    return bold, regular


def _add_lower_third(video_path: Path, anchor: dict, out_path: Path) -> bool:
    """Burn a lower-third name/title graphic onto the video using ffmpeg."""
    import shutil

    lt = anchor["lower_third"]
    name  = lt["name"]
    title = lt["title"]
    color = lt["color_accent"].lstrip("#")

    bold_font, reg_font = _find_fonts()
    bold_arg = f":fontfile={bold_font}" if bold_font else ""
    reg_arg  = f":fontfile={reg_font}"  if reg_font  else ""

    filter_complex = (
        f"drawbox=x=0:y=ih-80:w=iw:h=80:color=0x{color}@0.85:t=fill,"
        f"drawtext=text='{name}':fontcolor=white:fontsize=28:x=20:y=h-65{bold_arg},"
        f"drawtext=text='{title}':fontcolor=white@0.85:fontsize=18:x=20:y=h-35{reg_arg}"
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
        shutil.copy2(video_path, out_path)
        return False


def render_preview(anchor: dict, script: str, api_key: str, static: bool = False) -> Path | None:
    aid = anchor["id"]
    name = anchor["name"]

    portrait = PORTRAITS_DIR / f"{aid}.png"
    if not portrait.exists():
        print(f"  [skip] No final portrait for {name}.")
        print(f"         Run: python scripts/anchors/generate_portraits.py --anchors {aid}")
        print(f"         Then: python scripts/anchors/generate_portraits.py --pick {aid} <1-4>")
        return None

    PREVIEWS_DIR.mkdir(parents=True, exist_ok=True)
    suffix = "_static_preview" if static else "_preview"
    final_out = PREVIEWS_DIR / f"{aid}{suffix}.mp4"

    mode_label = "static (Ken Burns)" if static else "lip-sync (SadTalker)"
    print(f"\nRendering preview [{mode_label}]: {name}")
    print(f"  Script: \"{script}\"")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        audio_path = tmp_path / f"{aid}.mp3"
        raw_video  = tmp_path / f"{aid}_raw.mp4"

        # 1. TTS
        print("  [1/3] Generating voice...")
        if not _tts(anchor, script, audio_path, api_key):
            return None

        # 2. Animation
        print("  [2/3] Animating portrait...")
        if static:
            if not _static_video(portrait, audio_path, raw_video):
                return None
        else:
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
    parser.add_argument("--static", action="store_true",
                        help="CPU-only mode: Ken Burns zoom instead of SadTalker lip-sync")
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
            render_preview(anchor, script, api_key, static=args.static)
    elif args.anchor:
        anchor = next((a for a in roster if a["id"] == args.anchor), None)
        if not anchor:
            print(f"Unknown anchor ID: {args.anchor}")
            print(f"Valid: {', '.join(a['id'] for a in roster)}")
            sys.exit(1)
        script = args.script or DEFAULT_SCRIPTS.get(anchor["id"], f"Hello, I'm {anchor['name']}.")
        render_preview(anchor, script, api_key, static=args.static)
    else:
        parser.print_help()
