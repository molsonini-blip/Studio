"""
Create and assign ElevenLabs voices for each news anchor using the
Voice Design API (generates a unique synthetic voice from descriptors).

Saves the assigned voice_id back into data/anchors/roster.json.

Usage:
    # Set API key first
    export ELEVENLABS_API_KEY=your_key_here   (Linux/Mac)
    $env:ELEVENLABS_API_KEY="your_key_here"   (Windows PowerShell)

    # Create voices for all anchors that don't have one yet
    python scripts/anchors/setup_voices.py

    # Create voices for specific anchors
    python scripts/anchors/setup_voices.py --anchors marcus_webb dana_reyes

    # Preview what a voice sounds like (generates a short sample)
    python scripts/anchors/setup_voices.py --preview marcus_webb

    # List all anchors and their voice status
    python scripts/anchors/setup_voices.py --status

ElevenLabs free tier: 10,000 chars/month — enough to preview all 12 anchors.
Get your API key at: https://elevenlabs.io
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import requests

ROSTER_PATH = Path("data/anchors/roster.json")
VOICES_DIR = Path("data/anchors/voices")
ELEVENLABS_BASE = "https://api.elevenlabs.io/v1"

# Sample script used when previewing a voice — short broadcast intro line
PREVIEW_SCRIPTS = {
    "marcus_webb":    "Good evening. I'm Marcus Webb. Here are tonight's top stories.",
    "dana_reyes":     "Good morning. I'm Dana Reyes, and we have a lot to cover today.",
    "james_callahan": "Good evening, everyone. James Callahan here. Let's get right to it.",
    "priya_nair":     "Good afternoon. I'm Priya Nair. Here is what you need to know.",
    "mei_lin_zhou":   "Good evening. I'm Mei-Lin Zhou. Tonight's headlines, straight ahead.",
    "tyler_brooks":   "Hey, I'm Tyler Brooks. Here's what's trending in the news today.",
    "sofia_okafor":   "Hi everyone, Sofia Okafor here. Let's break down today's stories.",
    "carlos_mendez":  "Good evening. Carlos Mendez with you tonight. Here are the stories that matter.",
    "aisha_thompson": "I'm Aisha Thompson. Breaking news tonight — here's what we know.",
    "kevin_park":     "Good evening. I'm Kevin Park. Tonight we're looking at the numbers behind the headlines.",
    "rachel_torres":  "Hey! Rachel Torres here. Here's what everyone is talking about today.",
    "layla_hassan":   "Good evening. I'm Layla Hassan. Tonight's top stories from around the world.",
}


def get_api_key() -> str:
    key = os.environ.get("ELEVENLABS_API_KEY", "")
    if not key:
        print("ERROR: ELEVENLABS_API_KEY environment variable not set.")
        print("Get your key at: https://elevenlabs.io")
        print("Then set it:")
        print('  Windows PowerShell: $env:ELEVENLABS_API_KEY="your_key"')
        print('  Linux/Mac: export ELEVENLABS_API_KEY="your_key"')
        sys.exit(1)
    return key


def load_roster() -> list[dict]:
    with open(ROSTER_PATH) as f:
        return json.load(f)


def save_roster(roster: list[dict]):
    with open(ROSTER_PATH, "w") as f:
        json.dump(roster, f, indent=2)


def headers(api_key: str) -> dict:
    return {"xi-api-key": api_key, "Content-Type": "application/json"}


def create_voice(anchor: dict, api_key: str) -> str | None:
    """Create a voice via ElevenLabs Voice Design and return the voice_id."""
    vd = anchor["voice_design"]
    name = f"Studio_{anchor['id']}"

    # Text must be >=100 chars for the preview API
    script = PREVIEW_SCRIPTS.get(anchor["id"], f"Hello, I am {anchor['name']}.")
    while len(script) < 100:
        script += " Stay with us for more coverage throughout the evening."

    description = (
        f"{vd['gender']}, {vd['age'].replace('_', ' ')}, {vd['accent']} accent. "
        f"{vd['tone']}. {vd['description']}"
    )

    # Step 1: generate preview — returns generated_voice_id + audio
    print(f"  Designing voice for {anchor['name']}...")
    resp = requests.post(
        f"{ELEVENLABS_BASE}/text-to-voice/create-previews",
        headers=headers(api_key),
        json={"voice_description": description, "text": script},
        timeout=60,
    )

    if resp.status_code != 200:
        print(f"  [error] Voice preview failed: {resp.status_code} {resp.text[:200]}")
        return None

    previews = resp.json().get("previews", [])
    if not previews:
        print(f"  [error] No previews returned: {resp.json()}")
        return None

    generated_voice_id = previews[0].get("generated_voice_id")
    if not generated_voice_id:
        print(f"  [error] No generated_voice_id in preview: {previews[0]}")
        return None

    # Step 2: save the preview as a permanent voice in the library
    save_resp = requests.post(
        f"{ELEVENLABS_BASE}/text-to-voice/create-voice-from-preview",
        headers=headers(api_key),
        json={
            "voice_name": name,
            "voice_description": description,
            "generated_voice_id": generated_voice_id,
            "labels": {"anchor": anchor["name"], "project": "studio"},
        },
        timeout=30,
    )

    if save_resp.status_code != 200:
        print(f"  [error] Save voice failed: {save_resp.status_code} {save_resp.text[:200]}")
        return None

    voice_id = save_resp.json().get("voice_id")
    print(f"  Created: {name}  id={voice_id}")
    return voice_id


def preview_voice(anchor: dict, api_key: str):
    """Generate and save a preview MP3 for an anchor."""
    voice_id = anchor.get("elevenlabs_voice_id")
    if not voice_id:
        print(f"No voice assigned to {anchor['name']}. Run setup first.")
        return

    VOICES_DIR.mkdir(parents=True, exist_ok=True)
    out_path = VOICES_DIR / f"{anchor['id']}_preview.mp3"

    script = PREVIEW_SCRIPTS.get(anchor["id"], f"Hello, I am {anchor['name']}.")

    resp = requests.post(
        f"{ELEVENLABS_BASE}/text-to-speech/{voice_id}",
        headers={**headers(api_key), "Accept": "audio/mpeg"},
        json={
            "text": script,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
        },
        timeout=60,
    )

    if resp.status_code != 200:
        print(f"TTS failed: {resp.status_code} {resp.text[:200]}")
        return

    out_path.write_bytes(resp.content)
    print(f"Preview saved: {out_path}")
    print(f"Script: \"{script}\"")


def list_status(roster: list[dict]):
    print(f"\n{'Anchor':<20} {'Voice ID':<30} {'Status'}")
    print("-" * 65)
    for anchor in roster:
        vid = anchor.get("elevenlabs_voice_id") or "—"
        preview = "preview ✓" if (VOICES_DIR / f"{anchor['id']}_preview.mp3").exists() else ""
        print(f"{anchor['name']:<20} {vid:<30} {preview}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create ElevenLabs voices for news anchors")
    parser.add_argument("--anchors", nargs="+", metavar="ID",
                        help="Anchor IDs to process (default: all without a voice)")
    parser.add_argument("--preview", metavar="ANCHOR_ID",
                        help="Generate a preview audio clip for an anchor")
    parser.add_argument("--preview-all", action="store_true",
                        help="Generate preview clips for all anchors with voices")
    parser.add_argument("--status", action="store_true",
                        help="Show voice assignment status for all anchors")
    parser.add_argument("--force", action="store_true",
                        help="Re-create voices even if already assigned")
    args = parser.parse_args()

    roster = load_roster()
    VOICES_DIR.mkdir(parents=True, exist_ok=True)

    if args.status:
        list_status(roster)
        sys.exit(0)

    api_key = get_api_key()

    if args.preview:
        anchor = next((a for a in roster if a["id"] == args.preview), None)
        if not anchor:
            print(f"Unknown anchor: {args.preview}")
            sys.exit(1)
        preview_voice(anchor, api_key)
        sys.exit(0)

    if args.preview_all:
        for anchor in roster:
            if anchor.get("elevenlabs_voice_id"):
                preview_voice(anchor, api_key)
                time.sleep(1)
        sys.exit(0)

    # Determine which anchors to process
    if args.anchors:
        ids = set(args.anchors)
        targets = [a for a in roster if a["id"] in ids]
    else:
        targets = [a for a in roster if not a.get("elevenlabs_voice_id") or args.force]

    if not targets:
        print("All anchors already have voices. Use --force to recreate, or --status to review.")
        sys.exit(0)

    print(f"Creating voices for {len(targets)} anchor(s)...")
    updated = False
    for anchor in targets:
        voice_id = create_voice(anchor, api_key)
        if voice_id:
            anchor["elevenlabs_voice_id"] = voice_id
            updated = True
        time.sleep(2)  # polite delay between API calls

    if updated:
        save_roster(roster)
        print(f"\nRoster updated: {ROSTER_PATH}")

    list_status(roster)
