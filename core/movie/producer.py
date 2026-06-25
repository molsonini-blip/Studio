"""
Jim Hall movie — ElevenLabs TTS producer.

For each scene, sends the refined narration to ElevenLabs and saves:
  outputs/jim_hall/audio/{scene_id:02d}_{slug}.mp3
  outputs/jim_hall/scripts/{scene_id:02d}_{slug}.txt
  outputs/jim_hall/manifest.json
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

import requests

from core.movie.scenes import NARRATOR_VOICE_ID

_ELEVENLABS_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

# Narrator voice settings — documentary style: stable, warm, slightly slower
_VOICE_SETTINGS = {
    "stability": 0.72,
    "similarity_boost": 0.80,
    "style": 0.15,
    "use_speaker_boost": True,
}

# Documentary narration: slightly slower, natural pace
_MODEL_ID = "eleven_monolingual_v1"


def _generate_tts(text: str, api_key: str, out_path: Path) -> bool:
    """Returns True on success."""
    url = _ELEVENLABS_URL.format(voice_id=NARRATOR_VOICE_ID)
    try:
        resp = requests.post(
            url,
            headers={"xi-api-key": api_key, "Content-Type": "application/json"},
            json={
                "text": text,
                "model_id": _MODEL_ID,
                "voice_settings": _VOICE_SETTINGS,
            },
            timeout=120,
        )
        resp.raise_for_status()
        out_path.write_bytes(resp.content)
        return True
    except Exception as e:
        print(f"    [tts] ERROR for {out_path.name}: {e}")
        return False


def produce_movie(
    scenes: list[dict],
    output_root: Path,
    api_key: str,
    dry_run: bool = False,
    retry_existing: bool = False,
) -> Path:
    """
    Generates TTS audio for all scenes.
    Returns path to the manifest JSON.

    scenes: list of scene dicts with 'refined_vo' field (from narrator.refine_all_scenes)
    output_root: base directory (e.g. /opt/studio/outputs/jim_hall)
    dry_run: if True, skip TTS and just write scripts
    retry_existing: if False, skip scenes where audio already exists
    """
    audio_dir = output_root / "audio"
    scripts_dir = output_root / "scripts"
    audio_dir.mkdir(parents=True, exist_ok=True)
    scripts_dir.mkdir(parents=True, exist_ok=True)

    manifest = []

    for scene in scenes:
        sid = scene["id"]
        slug = scene["slug"]
        vo_text = scene.get("refined_vo", scene["vo"])
        prefix = f"{sid:02d}_{slug}"

        audio_path = audio_dir / f"{prefix}.mp3"
        script_path = scripts_dir / f"{prefix}.txt"

        # Always write the script
        script_path.write_text(vo_text, encoding="utf-8")

        # TTS
        audio_exists = audio_path.exists() and audio_path.stat().st_size > 1000
        if dry_run:
            print(f"  [dry] scene {sid:02d} {slug} — script saved, TTS skipped")
            audio_ok = False
        elif audio_exists and not retry_existing:
            print(f"  [skip] scene {sid:02d} {slug} — audio exists ({audio_path.stat().st_size // 1024}KB)")
            audio_ok = True
        else:
            print(f"  [tts] scene {sid:02d} {slug} — generating audio...")
            audio_ok = _generate_tts(vo_text, api_key, audio_path)
            if audio_ok:
                size_kb = audio_path.stat().st_size // 1024
                print(f"    saved {size_kb}KB -> {audio_path.name}")
            # Respect ElevenLabs rate limit (avoid 429)
            time.sleep(0.5)

        manifest.append({
            "id": sid,
            "slug": slug,
            "title": scene["title"],
            "duration_sec": scene.get("duration_sec"),
            "priority": scene.get("priority"),
            "music": scene.get("music"),
            "script_path": str(script_path.relative_to(output_root)),
            "audio_path": str(audio_path.relative_to(output_root)) if audio_ok else None,
            "vo_chars": len(vo_text),
            "quote": scene.get("quote"),
        })

    manifest_path = output_root / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\n[producer] manifest -> {manifest_path}")
    return manifest_path
