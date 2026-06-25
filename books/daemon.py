#!/usr/bin/env python3
"""
Books production daemon — runs forever on EdgeExpert.

Cycles through all book genres. For each genre:
  - Generates a new series concept (Ollama reads prior series, generates something new)
  - Writes every book in the series (20-22 for romance, 10 for others)
  - Each book: outline + all chapters + EPUB
  - Once series complete: generates a new series with different characters

Never stops. Never repeats. Completely autonomous.

Usage (on EdgeExpert):
  cd /opt/studio
  nohup venv/bin/python -m books.daemon > logs/books_daemon.log 2>&1 &
  echo $! > logs/books_daemon.pid

Monitor:
  tail -f /opt/studio/logs/books_daemon.log

Stop:
  kill $(cat /opt/studio/logs/books_daemon.pid)
"""
from __future__ import annotations

import json
import sys
import time
import traceback
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from books.genres.definitions import GENRES
from books.series_generator import generate_series, save_series, load_prior_series, SeriesBible
from books.chapter_writer import write_book
from books.epub_writer import build_epub

BOOKS_DIR = ROOT / "books" / "output"
LOGS_DIR = ROOT / "logs"
STATE_FILE = ROOT / "books" / "daemon_state.json"

# Genre rotation order — romance first (most commercial), then others
GENRE_ORDER = [
    "romance", "thriller", "mystery", "sci_fi",
    "horror", "fantasy", "historical", "western",
]

_MODEL = "llama3.1:8b"
_LOG_PREFIX = "[books_daemon]"


def log(msg: str) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {_LOG_PREFIX} {msg}", flush=True)


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {
        "genre_index": 0,
        "total_series": 0,
        "total_books": 0,
        "total_chapters": 0,
        "current_series": None,
        "current_book": 0,
    }


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def get_or_generate_series(genre_name: str, state: dict) -> tuple[SeriesBible, Path]:
    """
    Return the current in-progress series for this genre,
    or generate a new one if none exists / previous completed.
    """
    genre_def = GENRES[genre_name]
    genre_output_dir = BOOKS_DIR / genre_name

    # Check if there's an in-progress series
    if state.get("current_series") and state.get("current_series_genre") == genre_name:
        series_dir = Path(state["current_series"])
        series_json = series_dir / "series.json"
        if series_json.exists():
            log(f"  Resuming series: {series_dir.name}")
            raw = json.loads(series_json.read_text())
            books_raw = raw.pop("books", [])
            from books.series_generator import BookEntry
            books = [BookEntry(**b) for b in books_raw]
            series = SeriesBible(**raw, books=books)
            return series, series_dir

    # Generate new series
    prior = load_prior_series(genre_name, BOOKS_DIR)
    log(f"  Prior series in {genre_name}: {len(prior)}")
    log(f"  Generating new series concept...")
    series = generate_series(genre_def, prior_series=prior, model=_MODEL)
    log(f"  Series: '{series.series_title}'")
    log(f"  Setting: {series.setting}")
    log(f"  Books planned: {len(series.books)}")

    series_dir = save_series(series, BOOKS_DIR)
    state["current_series"] = str(series_dir)
    state["current_series_genre"] = genre_name
    state["current_book"] = 0
    save_state(state)
    return series, series_dir


def produce_book(series: SeriesBible, book_entry, genre_name: str, series_dir: Path) -> bool:
    """Write all chapters and build EPUB for one book. Returns True on success."""
    genre_def = GENRES[genre_name]
    log(f"  Book #{book_entry.number}: {book_entry.title}")
    log(f"    Protagonist: {book_entry.protagonist} | Trope: {book_entry.trope}")
    log(f"    {book_entry.logline}")

    try:
        book_dir = write_book(
            series=series,
            book=book_entry,
            genre_def=genre_def,
            output_dir=series_dir,
            model=_MODEL,
            log_fn=log,
        )

        # Build EPUB
        log(f"    Building EPUB...")
        epub_path = build_epub(
            series_title=series.series_title,
            book_title=book_entry.title,
            book_number=book_entry.number,
            author="AI Studio",
            genre=genre_name,
            book_dir=book_dir,
        )
        log(f"    ✓ EPUB: {epub_path.name}")
        return True

    except Exception as e:
        log(f"    ✗ Error: {e}")
        log(traceback.format_exc())
        return False


def main() -> None:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    BOOKS_DIR.mkdir(parents=True, exist_ok=True)

    state = load_state()
    log(f"Starting books daemon. Total series: {state['total_series']} | Books: {state['total_books']}")

    while True:
        genre_name = GENRE_ORDER[state["genre_index"] % len(GENRE_ORDER)]
        log(f"\n{'='*60}")
        log(f"Genre: {genre_name.upper()}")

        try:
            series, series_dir = get_or_generate_series(genre_name, state)
            start_book = state.get("current_book", 0)

            log(f"  Writing books {start_book + 1}–{len(series.books)} of '{series.series_title}'")

            all_done = True
            for book_entry in series.books[start_book:]:
                success = produce_book(series, book_entry, genre_name, series_dir)
                if success:
                    state["current_book"] = book_entry.number
                    state["total_books"] = state.get("total_books", 0) + 1
                    save_state(state)
                else:
                    all_done = False
                    # Continue to next book anyway
                    state["current_book"] = book_entry.number
                    save_state(state)

                # Brief pause between books so other daemons get GPU time
                time.sleep(30)

            if all_done:
                log(f"  Series '{series.series_title}' COMPLETE — {len(series.books)} books written")
            else:
                log(f"  Series '{series.series_title}' finished with some errors")

            # Update state — move to next genre, clear current series
            state["total_series"] = state.get("total_series", 0) + 1
            state["genre_index"] = (state["genre_index"] + 1) % len(GENRE_ORDER)
            state["current_series"] = None
            state["current_series_genre"] = None
            state["current_book"] = 0
            state["last_completed"] = {
                "series": series.series_title,
                "genre": genre_name,
                "books": len(series.books),
                "timestamp": datetime.now().isoformat(),
            }
            save_state(state)

            # After completing a full rotation, romance gets another series immediately
            if genre_name == "romance":
                log("  Romance series complete — starting new romance series immediately")
            else:
                log(f"  Moving to next genre in 60s...")
                time.sleep(60)

        except KeyboardInterrupt:
            log("Interrupted by user.")
            break
        except Exception as e:
            log(f"ERROR in genre {genre_name}: {e}")
            log(traceback.format_exc())
            log("Advancing to next genre in 120s...")
            time.sleep(120)
            state["genre_index"] = (state["genre_index"] + 1) % len(GENRE_ORDER)
            state["current_series"] = None
            state["current_book"] = 0
            save_state(state)


if __name__ == "__main__":
    main()
