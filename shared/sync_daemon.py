#!/usr/bin/env python3
"""
Sync daemon — copies finished media from EdgeExpert working dirs to the readyshare.

Runs every 10 minutes, checking for new EPUBs, MP3s, and screenplays.
Copies to /mnt/ai_projects/Finished_Media/<type>/<genre>/<series>/

Usage (on EdgeExpert):
  cd /opt/studio
  nohup venv/bin/python -m shared.sync_daemon > logs/sync_daemon.log 2>&1 &
  echo $! > logs/sync_daemon.pid
"""
from __future__ import annotations

import shutil
import time
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

SHARE = Path("/mnt/ai_projects/Finished_Media")
BOOKS_SRC = ROOT / "books" / "output"
MUSIC_SRC = ROOT / "music" / "albums"

GENRE_MAP = {
    "romance": "Romance", "thriller": "Thriller", "mystery": "Mystery",
    "sci_fi": "Sci-Fi", "horror": "Horror", "fantasy": "Fantasy",
    "historical": "Historical", "western": "Western",
    "soundtracks": "Soundtracks", "rock": "Rock", "country": "Country",
    "hip_hop": "Hip-Hop", "electronic": "Electronic", "jazz": "Jazz",
    "classical": "Classical", "pop": "Pop",
}

_LOG_PREFIX = "[sync_daemon]"
INTERVAL = 600  # 10 minutes


def log(msg: str) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {_LOG_PREFIX} {msg}", flush=True)


def sync_books() -> int:
    """Copy finished EPUBs to the share. Returns count of new files copied."""
    copied = 0
    if not BOOKS_SRC.exists():
        return 0

    for genre_dir in BOOKS_SRC.iterdir():
        if not genre_dir.is_dir():
            continue
        genre_label = GENRE_MAP.get(genre_dir.name, genre_dir.name.title())
        dest_genre = SHARE / "Books" / genre_label

        for series_dir in genre_dir.iterdir():
            if not series_dir.is_dir():
                continue
            dest_series = dest_genre / series_dir.name
            dest_series.mkdir(parents=True, exist_ok=True)

            # Copy series.json
            series_json = series_dir / "series.json"
            if series_json.exists():
                dst = dest_series / "series.json"
                if not dst.exists() or dst.stat().st_mtime < series_json.stat().st_mtime:
                    shutil.copy2(series_json, dst)

            # Copy all EPUBs from book subdirectories
            for epub in series_dir.rglob("*.epub"):
                dst = dest_series / epub.name
                if not dst.exists():
                    shutil.copy2(epub, dst)
                    log(f"  Book: {genre_label}/{series_dir.name}/{epub.name}")
                    copied += 1

    return copied


def sync_music() -> int:
    """Copy finished MP3s to the share, organized by album. Returns count copied."""
    copied = 0
    if not MUSIC_SRC.exists():
        return 0

    for genre_dir in MUSIC_SRC.iterdir():
        if not genre_dir.is_dir():
            continue
        genre_label = GENRE_MAP.get(genre_dir.name, genre_dir.name.title())
        dest_genre = SHARE / "Music" / genre_label

        for album_dir in genre_dir.iterdir():
            if not album_dir.is_dir():
                continue
            dest_album = dest_genre / album_dir.name
            dest_album.mkdir(parents=True, exist_ok=True)

            # Copy album.json (metadata/liner notes)
            album_json = album_dir / "album.json"
            if album_json.exists():
                dst = dest_album / "album.json"
                if not dst.exists():
                    shutil.copy2(album_json, dst)

            # Copy all MP3s
            for mp3 in album_dir.glob("*.mp3"):
                dst = dest_album / mp3.name
                if not dst.exists():
                    shutil.copy2(mp3, dst)
                    log(f"  Music: {genre_label}/{album_dir.name}/{mp3.name}")
                    copied += 1

    return copied


def check_share_mounted() -> bool:
    return SHARE.exists() and SHARE.is_dir()


def main() -> None:
    log(f"Starting sync daemon. Interval: {INTERVAL}s")
    log(f"Share: {SHARE}")

    while True:
        if not check_share_mounted():
            log("WARNING: Share not mounted. Retrying in 60s...")
            time.sleep(60)
            continue

        try:
            books = sync_books()
            music = sync_music()
            if books or music:
                log(f"Synced: {books} books, {music} music tracks")
            else:
                log("Nothing new to sync")
        except Exception as e:
            log(f"Sync error: {e}")

        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
