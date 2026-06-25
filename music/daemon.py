#!/usr/bin/env python3
"""
Music production daemon — runs forever on EdgeExpert.

Cycles through all 8 genres continuously, generating a complete album
for each genre before moving to the next. Never stops. Never repeats.

Ollama generates the concept and song ideas.
MusicGen (local, free) produces instrumentals.
Suno API produces vocal tracks for pop, hip-hop, country, rock.

Usage (on EdgeExpert):
  cd /opt/studio
  nohup venv/bin/python -m music.daemon > logs/music_daemon.log 2>&1 &
  echo $! > logs/music_daemon.pid

Monitor:
  tail -f /opt/studio/logs/music_daemon.log

Stop:
  kill $(cat /opt/studio/logs/music_daemon.pid)
"""
from __future__ import annotations

import json
import os
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from music.album import generate_album, save_album, load_prior_albums, AlbumConcept
from music.ideas import GENRES
from music.pipeline import LocalMusicGenBackend, SunoBackend, PlaceholderBackend, run as produce_track
from shared import budget, gpu_lock

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

ALBUMS_DIR = ROOT / "music" / "albums"
LOGS_DIR = ROOT / "logs"
STATE_FILE = ROOT / "music" / "daemon_state.json"

# Genres that benefit from Suno (vocals) in addition to MusicGen (instrumentals)
VOCAL_GENRES = {"pop", "hip_hop", "country", "rock"}

# How long to wait between albums (gives other daemons GPU time)
INTER_ALBUM_PAUSE = 300  # 5 minutes

# MusicGen model — stereo-large for best quality
MUSICGEN_MODEL = "facebook/musicgen-stereo-large"
TRACK_DURATION = 45  # seconds per track

_LOG_PREFIX = "[music_daemon]"


def log(msg: str) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {_LOG_PREFIX} {msg}", flush=True)


# ---------------------------------------------------------------------------
# State — tracks what's been done so we never repeat
# ---------------------------------------------------------------------------

def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {"genre_index": 0, "total_albums": 0, "total_tracks": 0}


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


# ---------------------------------------------------------------------------
# Album production
# ---------------------------------------------------------------------------

def produce_album(album: AlbumConcept, album_dir: Path) -> int:
    """Generate audio for all tracks in an album. Returns number of successes."""
    use_suno = album.genre in VOCAL_GENRES and bool(os.environ.get("SUNO_API_KEY"))
    suno = SunoBackend() if use_suno else None

    # Lazy-load MusicGen once per album (expensive)
    musicgen = LocalMusicGenBackend(model=MUSICGEN_MODEL, duration=TRACK_DURATION)

    successes = 0
    for i, track in enumerate(album.tracks):
        log(f"  Track {i+1}/{len(album.tracks)}: {track.title}")
        out_path = album_dir / f"{i+1:02d}_{track.title[:40].replace(' ', '_')}.mp3"
        out_path = Path("".join(c if c.isalnum() or c in "/_-." else "" for c in str(out_path)))

        # Try Suno for vocal genres (alternates with MusicGen)
        backend = suno if (suno and i % 3 == 0) else musicgen

        with gpu_lock.acquire(f"music_daemon:track:{track.title}"):
            result = produce_track(track, index=i, backend=backend)

        if result.success:
            successes += 1
            # Move output to album directory
            if result.output_path.exists() and result.output_path != out_path:
                out_path.parent.mkdir(parents=True, exist_ok=True)
                result.output_path.rename(out_path)
                # Move metadata JSON too
                meta = result.output_path.with_suffix(".json")
                if meta.exists():
                    meta.rename(out_path.with_suffix(".json"))
            log(f"    ✓ Saved: {out_path.name}")
        else:
            log(f"    ✗ Failed: {result.error}")

        time.sleep(5)  # brief pause between tracks

    return successes


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def main() -> None:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    ALBUMS_DIR.mkdir(parents=True, exist_ok=True)

    genres = list(GENRES.keys())
    state = load_state()
    log(f"Starting music daemon. {len(genres)} genres. Total albums so far: {state['total_albums']}")

    while True:
        genre = genres[state["genre_index"] % len(genres)]
        log(f"=== Genre: {genre.upper()} | Album #{state['total_albums'] + 1} ===")

        try:
            # Load prior albums to avoid repetition
            prior = load_prior_albums(genre, ALBUMS_DIR)
            log(f"  Prior albums in this genre: {len(prior)}")

            # Generate album concept via Ollama
            log("  Generating album concept...")
            album = generate_album(genre, prior_albums=prior, track_count=10)
            log(f"  Album: '{album.title}' by {album.artist} ({album.subgenre}, {album.year})")
            log(f"  Concept: {album.concept[:80]}...")

            # Save concept metadata
            album_dir = save_album(album, ALBUMS_DIR)
            log(f"  Saved to: {album_dir}")

            # Produce audio tracks
            log(f"  Producing {len(album.tracks)} tracks...")
            successes = produce_album(album, album_dir)
            log(f"  Complete: {successes}/{len(album.tracks)} tracks produced")

            # Update state
            state["genre_index"] = (state["genre_index"] + 1) % len(genres)
            state["total_albums"] = state.get("total_albums", 0) + 1
            state["total_tracks"] = state.get("total_tracks", 0) + successes
            state["last_album"] = {
                "title": album.title, "artist": album.artist,
                "genre": genre, "tracks": successes,
                "timestamp": datetime.now().isoformat(),
            }
            save_state(state)

            log(f"  Waiting {INTER_ALBUM_PAUSE}s before next album...")
            time.sleep(INTER_ALBUM_PAUSE)

        except KeyboardInterrupt:
            log("Interrupted by user.")
            break
        except Exception as e:
            log(f"ERROR: {e}")
            log(traceback.format_exc())
            log("Continuing in 60s...")
            time.sleep(60)
            # Still advance genre so we don't get stuck on one broken genre
            state["genre_index"] = (state["genre_index"] + 1) % len(genres)
            save_state(state)


if __name__ == "__main__":
    main()
