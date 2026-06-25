#!/usr/bin/env python3
"""
Chapter generator — writes romance novel chapters via Ollama.

Takes a BookSynopsis and generates full chapter text, one chapter at a time.
Saves progress so you can resume if interrupted.

Usage:
  # Generate all chapters for book 1 of a series:
  python -m books.romance.chapter_generator \
    --series books/romance/series/navy_seals.json --book 1

  # Generate a specific chapter:
  python -m books.romance.chapter_generator \
    --series books/romance/series/navy_seals.json --book 1 --chapter 3

  # Generate from a standalone synopsis JSON:
  python -m books.romance.chapter_generator --synopsis my_book.json

  # Resume an in-progress book:
  python -m books.romance.chapter_generator \
    --series books/romance/series/navy_seals.json --book 1 --resume
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from shared import ollama
from books.romance.ideas import BookSynopsis, SeriesConcept

CHAPTERS_PER_BOOK = 20
WORDS_PER_CHAPTER = 3000   # ~60k words / 20 chapters

_CHAPTER_SYSTEM = """You are a bestselling romance novelist. You write vivid, fast-paced chapters
that keep readers turning pages. Your prose is clear, emotional, and never purple.

RULES:
1. Show, don't tell. Let action and dialogue carry emotion.
2. Every chapter must end on a hook — tension, revelation, or a moment of connection.
3. Dialogue should feel natural and move the story forward.
4. Use sensory details sparingly but effectively.
5. Maintain consistent character voice and motivation.
6. Target {word_count} words. Write the full chapter — do not summarize or skip ahead.
7. Return ONLY the chapter text. No chapter number header, no preamble."""

_OUTLINE_SYSTEM = """You are a romance novelist planning a book chapter by chapter.
Return ONLY a JSON array of chapter outlines. No preamble.

Schema:
[
  {
    "chapter": 1,
    "title": "chapter title",
    "pov": "hero|heroine",
    "scene": "where and when",
    "events": "what happens",
    "emotional_beat": "what the reader should feel",
    "ends_on": "the hook / cliffhanger"
  }
]"""


def _outline_prompt(book: BookSynopsis) -> str:
    return (
        f"Romance novel: {book.title}\n"
        f"Hero: {book.hero}\n"
        f"Heroine: {book.heroine}\n"
        f"Central conflict: {book.conflict}\n"
        f"Opening hook: {book.hook}\n"
        f"Dark moment: {book.black_moment}\n"
        f"Resolution: {book.resolution}\n"
        f"Heat level: {book.heat_level}\n\n"
        f"Create a {CHAPTERS_PER_BOOK}-chapter outline. "
        f"Follow the romance arc: meet → attraction → obstacles → dark moment → HEA."
    )


def _chapter_prompt(book: BookSynopsis, outline: dict, prev_summary: str = "") -> str:
    prev = f"\nWhat happened before:\n{prev_summary}\n" if prev_summary else ""
    return (
        f"Novel: {book.title}\n"
        f"Hero: {book.hero}\n"
        f"Heroine: {book.heroine}\n"
        f"Heat level: {book.heat_level}\n"
        f"{prev}\n"
        f"Chapter {outline['chapter']}: {outline.get('title', '')}\n"
        f"POV: {outline.get('pov', 'heroine')}\n"
        f"Scene: {outline.get('scene', '')}\n"
        f"Events: {outline.get('events', '')}\n"
        f"Emotional beat: {outline.get('emotional_beat', '')}\n"
        f"End on: {outline.get('ends_on', '')}\n\n"
        f"Write this chapter now. Target {WORDS_PER_CHAPTER} words."
    )


def _summary_prompt(chapter_text: str, chapter_num: int) -> str:
    return (
        f"Summarize chapter {chapter_num} of this romance novel in 3-4 sentences "
        f"covering the key events, emotional beats, and where characters end up.\n\n"
        f"Chapter:\n{chapter_text[:3000]}"
    )


def generate_outline(book: BookSynopsis, model: str = ollama._DEFAULT_MODEL) -> list[dict]:
    """Generate a chapter-by-chapter outline for a book."""
    raw = ollama.call_json(
        _outline_prompt(book),
        system=_OUTLINE_SYSTEM,
        model=model,
        temperature=0.8,
        max_tokens=4000,
    )
    return raw if isinstance(raw, list) else raw.get("chapters", [])


def generate_chapter(
    book: BookSynopsis,
    outline: dict,
    prev_summary: str = "",
    model: str = ollama._DEFAULT_MODEL,
) -> str:
    """Generate full chapter text."""
    system = _CHAPTER_SYSTEM.format(word_count=WORDS_PER_CHAPTER)
    return ollama.call(
        _chapter_prompt(book, outline, prev_summary),
        system=system,
        model=model,
        temperature=0.85,
        max_tokens=4000,
    )


def summarize_chapter(text: str, chapter_num: int, model: str = ollama._DEFAULT_MODEL) -> str:
    return ollama.call(
        _summary_prompt(text, chapter_num),
        model=model,
        temperature=0.3,
        max_tokens=300,
    )


def get_output_dir(series_name: str, book_num: int) -> Path:
    base = Path(__file__).parent / "output" / series_name / f"book_{book_num:02d}"
    base.mkdir(parents=True, exist_ok=True)
    return base


def run_book(
    book: BookSynopsis,
    series_name: str,
    resume: bool = False,
    target_chapters: list[int] | None = None,
    model: str = ollama._DEFAULT_MODEL,
) -> Path:
    """Generate all chapters for a book. Returns output directory."""
    out_dir = get_output_dir(series_name, book.book_number)
    outline_path = out_dir / "outline.json"

    # Load or generate outline
    if outline_path.exists() and resume:
        outline = json.loads(outline_path.read_text())
        print(f"  Loaded existing outline ({len(outline)} chapters)")
    else:
        print(f"  Generating outline for '{book.title}' ...")
        outline = generate_outline(book, model=model)
        outline_path.write_text(json.dumps(outline, indent=2))
        print(f"  Outline saved ({len(outline)} chapters)")

    chapters_to_write = target_chapters or list(range(1, len(outline) + 1))
    prev_summary = ""

    for ch_num in chapters_to_write:
        ch_path = out_dir / f"chapter_{ch_num:02d}.txt"
        summary_path = out_dir / f"chapter_{ch_num:02d}_summary.txt"

        if ch_path.exists() and resume:
            print(f"  Chapter {ch_num}: already exists, skipping")
            if summary_path.exists():
                prev_summary = summary_path.read_text()
            continue

        ch_outline = next((c for c in outline if c.get("chapter") == ch_num), None)
        if not ch_outline:
            print(f"  Chapter {ch_num}: no outline entry, skipping")
            continue

        print(f"  Writing chapter {ch_num}: {ch_outline.get('title', '')} ...")
        text = generate_chapter(book, ch_outline, prev_summary, model=model)
        ch_path.write_text(text, encoding="utf-8")

        print(f"    Summarizing ...")
        prev_summary = summarize_chapter(text, ch_num, model=model)
        summary_path.write_text(prev_summary, encoding="utf-8")
        print(f"    Done. (~{len(text.split())} words)")

    return out_dir


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate romance novel chapters")
    parser.add_argument("--series", help="Path to series JSON file")
    parser.add_argument("--book", type=int, default=1, help="Book number (default: 1)")
    parser.add_argument("--synopsis", help="Path to standalone book synopsis JSON")
    parser.add_argument("--chapter", type=int, default=0,
                        help="Generate only this chapter number (0 = all)")
    parser.add_argument("--resume", action="store_true",
                        help="Skip chapters that already exist")
    parser.add_argument("--model", default=ollama._DEFAULT_MODEL)
    args = parser.parse_args()

    if args.series:
        series_data = json.loads(Path(args.series).read_text())
        series_name = Path(args.series).stem
        books_raw = series_data.get("books", [])
        book_raw = next((b for b in books_raw if b["book_number"] == args.book), None)
        if not book_raw:
            print(f"Book {args.book} not found in series.")
            sys.exit(1)
        book = BookSynopsis(**book_raw)
    elif args.synopsis:
        book = BookSynopsis(**json.loads(Path(args.synopsis).read_text()))
        series_name = Path(args.synopsis).stem
    else:
        print("Provide --series or --synopsis.")
        sys.exit(1)

    chapters = [args.chapter] if args.chapter else None
    print(f"\nGenerating: {book.title} (Book {book.book_number})")
    out = run_book(book, series_name, resume=args.resume,
                   target_chapters=chapters, model=args.model)
    print(f"\nOutput: {out}")


if __name__ == "__main__":
    main()
