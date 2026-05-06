from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import internetarchive as ia
import requests


def _bin(name: str) -> str:
    """Resolve a binary: check PATH first, then the current Python's venv bin dir."""
    found = shutil.which(name)
    if found:
        return found
    venv_bin = Path(sys.executable).parent / name
    if venv_bin.exists():
        return str(venv_bin)
    return name  # let subprocess raise a clear error

# Proven working queries for archive.org TV news content.
# The complex AND+OR collection filter returns 0 results — use targeted
# collection searches directly via the `fq` (filter query) parameter instead.
_COLLECTION_QUERIES = [
    ("mediatype:movies AND collection:tvnews", {}),
    ("mediatype:movies AND collection:tvarchive", {}),
    ("news anchor broadcast", {}),  # broad fallback — naturally surfaces tvnews items
]

# Search terms that pull news broadcast items
DEFAULT_QUERY = "news anchor broadcast"


@dataclass
class DownloadedClip:
    item_id: str
    title: str
    collection: str
    video_path: Path
    caption_path: Path | None   # .srt if available from archive
    audio_path: Path | None     # extracted .wav
    duration_sec: float = 0.0
    has_captions: bool = False


def search_archive(
    query: str = DEFAULT_QUERY,
    collections: list[str] | None = None,
    max_results: int = 50,
    min_duration_sec: int = 30,
) -> list[dict]:
    """Search Internet Archive for publicly downloadable broadcast news clips.

    Targets open-access TV news: small local stations uploaded to community
    collections. Excludes access-restricted items (copyright-blocked tvnews
    items from major networks require archive.org credentials to download).
    """
    seen: set[str] = set()
    results: list[dict] = []

    # Fetch a large pool from multiple passes; 401/403-restricted items are
    # skipped at download time. Major network tvnews items (FOXNEWS, CBS, etc.)
    # are often restricted while community uploads from small stations are open.
    if collections:
        passes = [(query, {"fq": f"collection:{c}"}) for c in collections]
        passes.append((query, {}))
    else:
        passes = [
            # Small/local station community archives — tend to be open access
            ("news broadcast mediatype:movies subject:news", {}),
            # Known open local-news collection (WHHI-TV Hilton Head and similar)
            ("news headlines local station mediatype:movies", {}),
            # General broad fallback
            (query, {}),
        ]

    fetch_per_pass = max(max_results * 4, 40)

    for q, extra_params in passes:
        if len(results) >= max_results:
            break
        try:
            search = ia.search_items(
                q,
                fields=["identifier", "title", "collection", "duration"],
                params={"rows": fetch_per_pass, "sort": "downloads desc", **extra_params},
            )
            for item in search:
                item_id = item.get("identifier")
                if not item_id or item_id in seen:
                    continue
                seen.add(item_id)
                raw_dur = item.get("duration")
                duration = float(raw_dur) if raw_dur is not None else None
                if duration is not None and duration < min_duration_sec:
                    continue
                results.append({
                    "id": item_id,
                    "title": item.get("title", ""),
                    "collection": item.get("collection", ""),
                    "duration": duration or 0.0,
                })
                if len(results) >= max_results:
                    break
        except Exception as e:
            print(f"  [search error] pass={q!r}: {e}")

    return results


def _has_caption_file(item_id: str) -> bool:
    """Check if an archive.org item has a subtitle/caption file."""
    try:
        item = ia.get_item(item_id)
        for f in item.files:
            if f.get("name", "").endswith((".srt", ".vtt", ".cc.srt")):
                return True
    except Exception:
        pass
    return False


def download_clip(
    item_id: str,
    output_dir: Path,
    max_duration_sec: int = 7200,
) -> DownloadedClip | None:
    """Download a single archive.org item: video + captions + extract audio."""
    output_dir = Path(output_dir)
    item_dir = output_dir / item_id
    item_dir.mkdir(parents=True, exist_ok=True)

    # ── Video + captions via internetarchive direct download ─────────────────
    # yt-dlp fails on tvnews items ("No video formats found") because these
    # are served as direct files, not via a player. Use ia.download() instead.
    video_path: Path | None = None

    existing_mp4 = list(item_dir.glob("*.mp4"))
    if existing_mp4:
        video_path = existing_mp4[0]
    else:
        try:
            item_obj = ia.get_item(item_id)
            # Find the best video file: prefer .mp4, accept .mpeg/.mov
            video_file = None
            srt_files = []
            for f in item_obj.files:
                fname = f.get("name", "")
                if fname.endswith(".mp4") and video_file is None:
                    video_file = fname
                elif fname.endswith((".mpeg", ".mov", ".mkv")) and video_file is None:
                    video_file = fname
                if fname.endswith((".srt", ".vtt", ".cc.srt")):
                    srt_files.append(fname)

            if not video_file:
                print(f"  [no video file] {item_id}")
                return None

            # Check duration before downloading to avoid huge files
            if max_duration_sec:
                for f in item_obj.files:
                    if f.get("name") == video_file:
                        raw_dur = f.get("length") or f.get("duration")
                        if raw_dur:
                            try:
                                if float(raw_dur) > max_duration_sec:
                                    print(f"  [skip: too long {float(raw_dur):.0f}s] {item_id}")
                                    return None
                            except (ValueError, TypeError):
                                pass
                        break

            files_to_get = [video_file] + srt_files
            item_obj.download(
                files=files_to_get,
                destdir=str(output_dir),
                ignore_existing=True,
                verbose=False,
            )

            downloaded = list(item_dir.glob("*.mp4")) + list(item_dir.glob("*.mpeg")) + \
                         list(item_dir.glob("*.mov")) + list(item_dir.glob("*.mkv"))
            if not downloaded:
                print(f"  [download produced no video] {item_id}")
                return None
            video_path = downloaded[0]
        except Exception as e:
            msg = str(e)
            if "401" in msg or "403" in msg:
                print(f"  [skip: access restricted] {item_id}")
            else:
                print(f"  [download error] {item_id}: {e}")
            return None

    # ── Find caption file ────────────────────────────────────────────────────
    srt_candidates = list(item_dir.glob("*.srt")) + list(item_dir.glob("*.vtt"))
    cap_path = srt_candidates[0] if srt_candidates else None

    # ── Extract audio ────────────────────────────────────────────────────────
    audio_path = item_dir / f"{item_id}.wav"
    if not audio_path.exists():
        try:
            subprocess.run([
                _bin("ffmpeg"), "-i", str(video_path),
                "-ar", "16000", "-ac", "1", "-f", "wav",
                str(audio_path), "-y", "-loglevel", "error"
            ], check=True, timeout=120)
        except Exception as e:
            print(f"  [audio extract error] {item_id}: {e}")
            audio_path = None

    # ── Duration ─────────────────────────────────────────────────────────────
    duration = 0.0
    try:
        result = subprocess.run(
            [_bin("ffprobe"), "-v", "error", "-show_entries", "format=duration",
             "-of", "json", str(video_path)],
            capture_output=True, text=True, timeout=10
        )
        duration = float(json.loads(result.stdout)["format"]["duration"])
    except Exception:
        pass

    return DownloadedClip(
        item_id=item_id,
        title="",
        collection="",
        video_path=video_path,
        caption_path=cap_path,
        audio_path=audio_path,
        duration_sec=duration,
        has_captions=cap_path is not None,
    )


def collect_dataset(
    output_dir: Path,
    query: str = DEFAULT_QUERY,
    collections: list[str] | None = None,
    max_clips: int = 100,
    max_duration_sec: int = 7200,
) -> list[DownloadedClip]:
    """Search and download a batch of news clips from archive.org."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Searching archive.org for: {query!r}")
    items = search_archive(query, collections, max_results=max_clips * 2)
    print(f"  Found {len(items)} candidates")

    clips: list[DownloadedClip] = []
    for item in items:
        if len(clips) >= max_clips:
            break
        print(f"  Downloading: {item['id']} ({item['duration']:.0f}s)")
        clip = download_clip(item["id"], output_dir, max_duration_sec)
        if clip:
            clip.title = item.get("title", "")
            clip.collection = item.get("collection", "")
            clips.append(clip)
            print(f"    saved — captions: {'yes' if clip.has_captions else 'no'}")
        time.sleep(1)  # polite delay

    print(f"Collected {len(clips)} clips to {output_dir}")
    return clips
