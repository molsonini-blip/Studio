"""
Album concept generator and structure.
Ollama generates the creative concept; pipeline.py produces the audio.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Optional
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from shared import ollama
from music.ideas import SongIdea, GENRES, generate_songs

_MODEL = "llama3.1:8b"

ALBUM_SYSTEM = """You are a creative music producer and A&R executive with deep knowledge of all genres.
You design complete album concepts — not generic collections, but fully realized artistic statements.

Each album must have:
- A distinct identity (era, mood, subgenre, influence)
- A concept or narrative arc across the tracks
- Variety within the genre — no two tracks should feel the same
- Liner notes that read like real album credits

Return ONLY valid JSON. No preamble, no explanation.

JSON schema:
{
  "title": "Album Title",
  "artist": "Artist Name (fictional)",
  "genre": "genre",
  "subgenre": "specific subgenre or style",
  "year": "fictional release year or era",
  "concept": "What this album is about — the artistic statement",
  "influences": ["Artist A", "Artist B", "Artist C"],
  "emotional_arc": "How the album flows emotionally from track 1 to last",
  "liner_notes": "2-3 sentences of liner note text, written in first person as the artist",
  "tracks": [
    {
      "title": "Track Title",
      "genre": "genre",
      "mood": "emotional feel",
      "tempo": "tempo description",
      "key": "musical key",
      "instruments": ["list", "of", "instruments"],
      "scene_or_context": "what moment this track captures",
      "lyric_hook": "one killer line or hook",
      "production_notes": "how this should sound, specific production direction",
      "duration_estimate": "e.g. 3:42"
    }
  ]
}"""


@dataclass
class AlbumConcept:
    title: str
    artist: str
    genre: str
    subgenre: str
    year: str
    concept: str
    influences: list[str]
    emotional_arc: str
    liner_notes: str
    tracks: list[SongIdea]
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    audio_files: list[str] = field(default_factory=list)


def generate_album(
    genre: str,
    prior_albums: list[dict] | None = None,
    track_count: int = 10,
    model: str = _MODEL,
) -> AlbumConcept:
    """Generate a complete album concept, avoiding repetition of prior albums."""
    g = GENRES.get(genre, {})
    avoid = ""
    if prior_albums:
        titles = [a.get("title", "") for a in prior_albums[-20:]]
        artists = [a.get("artist", "") for a in prior_albums[-20:]]
        concepts = [a.get("concept", "")[:60] for a in prior_albums[-10:]]
        avoid = (
            f"\n\nALREADY PRODUCED — create something DIFFERENT from these:\n"
            f"Titles: {', '.join(titles)}\n"
            f"Artists: {', '.join(artists)}\n"
            f"Recent concepts: {'; '.join(concepts)}\n"
            f"Do NOT repeat any of these artists, titles, or concepts."
        )

    prompt = (
        f"Genre: {genre}\n"
        f"Description: {g.get('description', genre)}\n"
        f"Style notes: {g.get('style_notes', '')}\n"
        f"Reference artists: {g.get('references', '')}\n"
        f"{avoid}\n\n"
        f"Design a complete {track_count}-track album. Make it feel like a real, "
        f"distinct artistic statement — not a generic collection. "
        f"Give it a specific era, sound, and story."
    )

    raw = ollama.call_json(prompt, system=ALBUM_SYSTEM, model=model,
                           temperature=0.9, max_tokens=4000)

    tracks = [
        SongIdea(
            title=t.get("title", "Untitled"),
            genre=t.get("genre", genre),
            mood=t.get("mood", ""),
            tempo=t.get("tempo", ""),
            key=t.get("key", ""),
            instruments=t.get("instruments", []),
            scene_or_context=t.get("scene_or_context", ""),
            lyric_hook=t.get("lyric_hook", ""),
            production_notes=t.get("production_notes", ""),
            duration_estimate=t.get("duration_estimate", ""),
        )
        for t in raw.get("tracks", [])
    ]

    return AlbumConcept(
        title=raw.get("title", f"{genre.title()} Album"),
        artist=raw.get("artist", "Unknown Artist"),
        genre=genre,
        subgenre=raw.get("subgenre", genre),
        year=raw.get("year", "2024"),
        concept=raw.get("concept", ""),
        influences=raw.get("influences", []),
        emotional_arc=raw.get("emotional_arc", ""),
        liner_notes=raw.get("liner_notes", ""),
        tracks=tracks,
    )


def save_album(album: AlbumConcept, base_dir: Path) -> Path:
    """Save album metadata JSON."""
    safe = "".join(c if c.isalnum() or c in " _-" else "" for c in album.title)
    safe = safe.strip().replace(" ", "_")[:50]
    album_dir = base_dir / album.genre / safe
    album_dir.mkdir(parents=True, exist_ok=True)
    path = album_dir / "album.json"
    d = asdict(album)
    path.write_text(json.dumps(d, indent=2))
    return album_dir


def load_prior_albums(genre: str, base_dir: Path) -> list[dict]:
    """Load metadata from all previously produced albums in this genre."""
    genre_dir = base_dir / genre
    if not genre_dir.exists():
        return []
    albums = []
    for album_json in sorted(genre_dir.rglob("album.json")):
        try:
            albums.append(json.loads(album_json.read_text()))
        except Exception:
            continue
    return albums
