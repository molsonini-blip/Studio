"""
Screenplay generator — converts completed book series into feature film screenplays.

Ratio rules (set by design, not user input):
  - Spy / government conspiracy / espionage series: 1:1 (every book → screenplay)
  - Thriller: 1:2 (every other book)
  - All other genres: 1:4 (every 4th book)

Rationale: Spy/espionage novels are the most naturally cinematic and commercially
viable (Bond, Bourne, Mission Impossible). Thrillers adapt at a higher rate than
literary fiction. Romance/fantasy/horror translate less directly and benefit from
compression into a single-film "best of the series" treatment.

Output: Final Draft-compatible plain text screenplay format saved to
  /mnt/ai_projects/Finished_Media/Books/_Screenplays/From_<Genre>/<Series>/<Title>.txt
  and a matching .json metadata file.
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from shared import ollama

_MODEL = "llama3.1:8b"
SHARE_BASE = Path("/mnt/ai_projects/Finished_Media/Books/_Screenplays")

_SPY_KEYWORDS = {
    "spy", "espionage", "cia", "mi6", "nsa", "fbi", "kgb", "assassin",
    "covert", "operative", "intelligence", "classified", "conspiracy",
    "government", "agency", "handler", "mole", "double agent", "black ops",
    "deep state", "surveillance", "whistleblower", "leak", "cover-up",
}

_SCREENPLAY_SYSTEM = """You are a professional Hollywood screenwriter adapting a novel into a feature film screenplay.
Write in standard screenplay format:

FADE IN:

INT./EXT. LOCATION - DAY/NIGHT

Action lines in present tense. Tight and visual.

CHARACTER NAME
    Dialogue here.

Keep it under 110 pages (pages ≈ minutes). A feature runs 90-110 minutes.
Three-act structure: Setup (25%), Confrontation (50%), Resolution (25%).
Every scene must MOVE — cut anything that doesn't advance plot or reveal character.

Return ONLY the screenplay text. No preamble. Start with FADE IN:"""

_OUTLINE_SYSTEM = """You are a development executive giving notes on a novel-to-film adaptation.
Identify: the single most cinematic story in this series, which characters to keep,
what subplots to cut, the core 3-act structure, and 5-7 key set pieces.
Return as JSON. No preamble."""


@dataclass
class ScreenplayMeta:
    series_title: str
    source_book_number: int
    source_book_title: str
    genre: str
    screenplay_title: str
    logline: str
    adaptation_ratio: str
    created_at: str


def _is_spy_series(series_data: dict) -> bool:
    """Detect spy/espionage/government conspiracy by scanning series content."""
    text = json.dumps(series_data).lower()
    hits = sum(1 for kw in _SPY_KEYWORDS if kw in text)
    return hits >= 3


def should_adapt(book_number: int, genre: str, series_data: dict) -> bool:
    """Return True if this book should be adapted into a screenplay."""
    if _is_spy_series(series_data):
        return True  # 1:1 for spy
    if genre == "thriller":
        return book_number % 2 == 1  # 1:2 for thriller (books 1, 3, 5...)
    # All others: 1:4 (books 1, 5, 9, 13...)
    return book_number % 4 == 1


def generate_adaptation_outline(series_data: dict, book_data: dict, model: str = _MODEL) -> dict:
    """Get Ollama's take on how to adapt this book for film."""
    prompt = (
        f"Series: {series_data.get('series_title')}\n"
        f"Genre: {series_data.get('genre')}\n"
        f"Setting: {series_data.get('setting')}\n"
        f"Book: #{book_data.get('number')} — {book_data.get('title')}\n"
        f"Protagonist: {book_data.get('protagonist')}\n"
        f"Logline: {book_data.get('logline')}\n"
        f"Conflict: {book_data.get('conflict')}\n\n"
        f"How do we adapt this into a 100-minute feature film?\n"
        f"Return JSON: {{\"adaptation_title\": \"...\", \"logline\": \"...\", "
        f"\"act_one\": \"...\", \"act_two\": \"...\", \"act_three\": \"...\", "
        f"\"key_scenes\": [\"scene1\", ...], \"cut_from_novel\": \"what to cut\"}}"
    )
    try:
        return ollama.call_json(prompt, system=_OUTLINE_SYSTEM, model=model, temperature=0.7)
    except Exception:
        return {"adaptation_title": book_data.get("title", ""), "logline": book_data.get("logline", "")}


def write_screenplay(series_data: dict, book_data: dict, outline: dict, model: str = _MODEL) -> str:
    """Write a full screenplay. Returns screenplay text."""
    prompt = (
        f"ADAPTATION: {outline.get('adaptation_title', book_data.get('title'))}\n"
        f"BASED ON: '{book_data.get('title')}' from the {series_data.get('series_title')} series\n"
        f"GENRE: {series_data.get('genre')}\n"
        f"SETTING: {series_data.get('setting')}\n\n"
        f"STORY OUTLINE:\n"
        f"Act One: {outline.get('act_one', '')}\n"
        f"Act Two: {outline.get('act_two', '')}\n"
        f"Act Three: {outline.get('act_three', '')}\n\n"
        f"KEY SCENES: {', '.join(outline.get('key_scenes', []))}\n\n"
        f"PROTAGONIST: {book_data.get('protagonist')}\n"
        f"CORE CONFLICT: {book_data.get('conflict')}\n\n"
        f"Write the complete feature screenplay. Aim for 90-100 pages."
    )
    return ollama.call(prompt, system=_SCREENPLAY_SYSTEM, model=model,
                       temperature=0.8, max_tokens=8000)


def adapt_book(
    series_dir: Path,
    book_number: int,
    genre: str,
    log_fn=print,
) -> Path | None:
    """
    Check if this book should be adapted, then write the screenplay.
    Returns the screenplay path if written, None if skipped.
    """
    series_json = series_dir / "series.json"
    if not series_json.exists():
        return None

    series_data = json.loads(series_json.read_text())
    books = series_data.get("books", [])
    book_data = next((b for b in books if b.get("number") == book_number), None)
    if not book_data:
        return None

    if not should_adapt(book_number, genre, series_data):
        ratio = "1:1" if _is_spy_series(series_data) else ("1:2" if genre == "thriller" else "1:4")
        log_fn(f"  [screenplay] Book #{book_number} skipped (ratio {ratio} for {genre})")
        return None

    ratio_label = "1:1 (spy)" if _is_spy_series(series_data) else ("1:2" if genre == "thriller" else "1:4")
    log_fn(f"  [screenplay] Adapting Book #{book_number}: {book_data.get('title')} ({ratio_label})")

    # Output path on share
    genre_label = {"sci_fi": "Sci-Fi"}.get(genre, genre.replace("_", " ").title())
    screenplay_dir = SHARE_BASE / f"From_{genre_label}" / series_data.get("series_title", "Unknown")
    screenplay_dir.mkdir(parents=True, exist_ok=True)

    safe = re.sub(r"[^\w\s-]", "", book_data.get("title", "screenplay")).strip().replace(" ", "_")[:50]
    screenplay_path = screenplay_dir / f"book{book_number:02d}_{safe}.txt"
    meta_path = screenplay_dir / f"book{book_number:02d}_{safe}.json"

    if screenplay_path.exists():
        log_fn(f"  [screenplay] Already exists: {screenplay_path.name}")
        return screenplay_path

    try:
        outline = generate_adaptation_outline(series_data, book_data)
        text = write_screenplay(series_data, book_data, outline)
        screenplay_path.write_text(text, encoding="utf-8")

        meta = ScreenplayMeta(
            series_title=series_data.get("series_title", ""),
            source_book_number=book_number,
            source_book_title=book_data.get("title", ""),
            genre=genre,
            screenplay_title=outline.get("adaptation_title", book_data.get("title", "")),
            logline=outline.get("logline", ""),
            adaptation_ratio=ratio_label,
            created_at=datetime.now().isoformat(),
        )
        meta_path.write_text(json.dumps(asdict(meta), indent=2))
        log_fn(f"  [screenplay] ✓ Written: {screenplay_path.name} ({len(text.split())} words)")
        return screenplay_path

    except Exception as e:
        log_fn(f"  [screenplay] Error: {e}")
        return None
