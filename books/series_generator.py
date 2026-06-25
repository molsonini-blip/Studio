"""
Series concept generator — Ollama creates the full series bible.
Reads prior series to ensure each new one is genuinely different.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from shared import ollama
from books.genres.definitions import GenreDef

_MODEL = "llama3.1:8b"

_SERIES_SYSTEM = """You are a professional book packager and series developer.
You create complete series bibles — fully realized fictional worlds with specific characters,
settings, and story arcs that sustain a long-running series.

Your series must be:
- Original and distinct — not a copy of any existing series
- Internally consistent — the world has rules and logic
- Character-rich — readers should want to return for the people, not just the plot
- Commercially viable — accessible but not dumbed-down

Return ONLY valid JSON. No preamble, no explanation, no markdown fences.

JSON schema:
{
  "series_title": "The Series Name",
  "tagline": "One-line hook",
  "genre": "genre name",
  "setting": "Where and when this is set — specific and vivid",
  "world_description": "2-3 sentences describing the world/community",
  "series_arc": "The overarching story or theme that runs through all books",
  "recurring_cast": [
    {
      "name": "Full Name",
      "role": "Their function in the series",
      "description": "Physical and personality description — specific, not generic",
      "backstory": "What made them who they are"
    }
  ],
  "books": [
    {
      "number": 1,
      "title": "Book Title",
      "protagonist": "Name of main character(s) for this book",
      "trope": "The core romance/story trope (enemies to lovers, etc.)",
      "logline": "One sentence — what this book is about",
      "conflict": "The central conflict keeping them apart or in danger",
      "resolution_hint": "How it resolves without spoiling"
    }
  ]
}"""


@dataclass
class BookEntry:
    number: int
    title: str
    protagonist: str
    trope: str
    logline: str
    conflict: str
    resolution_hint: str


@dataclass
class SeriesBible:
    series_title: str
    tagline: str
    genre: str
    setting: str
    world_description: str
    series_arc: str
    recurring_cast: list[dict]
    books: list[BookEntry]
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


def generate_series(
    genre_def: GenreDef,
    prior_series: list[dict] | None = None,
    model: str = _MODEL,
) -> SeriesBible:
    """Generate a complete series bible, learning from prior series."""

    avoid = ""
    if prior_series:
        existing = [
            f"'{s.get('series_title', '')}' ({s.get('setting', '')})"
            for s in prior_series[-15:]
        ]
        cast_names = []
        for s in prior_series[-5:]:
            for c in s.get("recurring_cast", [])[:3]:
                cast_names.append(c.get("name", ""))

        avoid = (
            f"\n\nALREADY WRITTEN — your new series MUST be completely different:\n"
            f"Existing series: {', '.join(existing)}\n"
            f"Used character names: {', '.join(cast_names[:20])}\n"
            f"Create a new setting, new character names, new community, new tone. "
            f"Do not repeat anything from the existing series."
        )

    prompt = (
        f"Genre: {genre_def.name}\n"
        f"Description: {genre_def.description}\n"
        f"Style: {genre_def.style_notes}\n"
        f"Reference authors: {', '.join(genre_def.references)}\n"
        f"Books in this series: {genre_def.books_per_series}\n"
        f"\n{genre_def.series_prompt}"
        f"{avoid}"
    )

    # Get the series bible (without books first — avoids token overflow)
    raw = ollama.call_json(
        prompt,
        system=_SERIES_SYSTEM,
        model=model,
        temperature=0.92,
        max_tokens=5000,
    )

    # Build book list in batches of 6 to avoid token limits
    all_books_raw = list(raw.get("books", []))
    target = genre_def.books_per_series
    if len(all_books_raw) < target:
        all_books_raw = _expand_books(
            series_title=raw.get("series_title", ""),
            setting=raw.get("setting", ""),
            existing_books=all_books_raw,
            target_count=target,
            genre_def=genre_def,
            model=model,
        )

    books = [
        BookEntry(
            number=b.get("number", i + 1),
            title=b.get("title", f"Book {i+1}"),
            protagonist=b.get("protagonist", ""),
            trope=b.get("trope", ""),
            logline=b.get("logline", ""),
            conflict=b.get("conflict", ""),
            resolution_hint=b.get("resolution_hint", ""),
        )
        for i, b in enumerate(all_books_raw)
    ]

    return SeriesBible(
        series_title=raw.get("series_title", f"New {genre_def.name.title()} Series"),
        tagline=raw.get("tagline", ""),
        genre=genre_def.name,
        setting=raw.get("setting", ""),
        world_description=raw.get("world_description", ""),
        series_arc=raw.get("series_arc", ""),
        recurring_cast=raw.get("recurring_cast", []),
        books=books,
    )


_EXPAND_SYSTEM = """You are a book series developer adding more books to an existing series.
Return ONLY a JSON array of new book objects. Continue the numbering from where the series left off.
Each object: {"number": N, "title": "...", "protagonist": "...", "trope": "...", "logline": "...", "conflict": "...", "resolution_hint": "..."}
No preamble. No markdown. Just the JSON array."""


def _expand_books(
    series_title: str,
    setting: str,
    existing_books: list[dict],
    target_count: int,
    genre_def: GenreDef,
    model: str,
) -> list[dict]:
    """Request more books in batches of 6 until we reach target_count."""
    books = list(existing_books)
    batch_size = 6

    while len(books) < target_count:
        remaining = target_count - len(books)
        batch = min(batch_size, remaining)
        next_num = len(books) + 1

        existing_titles = ", ".join(f"#{b.get('number',i+1)}: {b.get('title','')}"
                                    for i, b in enumerate(books[-6:]))
        prompt = (
            f"Series: {series_title} | Setting: {setting}\n"
            f"Genre: {genre_def.name} | Style: {genre_def.style_notes}\n"
            f"Last books already written: {existing_titles}\n\n"
            f"Add {batch} MORE books to this series (books #{next_num}–#{next_num+batch-1}). "
            f"Each new couple/protagonist must be different from all previous books. "
            f"Keep the same setting and world."
        )
        try:
            new_raw = ollama.call_json(prompt, system=_EXPAND_SYSTEM, model=model,
                                       temperature=0.88, max_tokens=2000)
            new_books = new_raw if isinstance(new_raw, list) else []
            if not new_books:
                break
            # Fix numbering
            for i, b in enumerate(new_books):
                b["number"] = next_num + i
            books.extend(new_books)
        except Exception:
            break

    return books


def save_series(series: SeriesBible, base_dir: Path) -> Path:
    """Save series bible to JSON."""
    safe = "".join(c if c.isalnum() or c in " _-" else "" for c in series.series_title)
    safe = safe.strip().replace(" ", "_")[:60]
    series_dir = base_dir / series.genre / safe
    series_dir.mkdir(parents=True, exist_ok=True)
    path = series_dir / "series.json"
    d = asdict(series)
    path.write_text(json.dumps(d, indent=2))
    return series_dir


def load_prior_series(genre: str, base_dir: Path) -> list[dict]:
    """Load all prior series bibles for this genre."""
    genre_dir = base_dir / genre
    if not genre_dir.exists():
        return []
    series_list = []
    for f in sorted(genre_dir.rglob("series.json")):
        try:
            series_list.append(json.loads(f.read_text()))
        except Exception:
            continue
    return series_list
