"""
Chapter writer — takes a series bible + book entry and writes every chapter via Ollama.
Resumes from where it left off if interrupted.
Auto-saves after each chapter.
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from shared import ollama
from books.genres.definitions import GenreDef
from books.series_generator import SeriesBible, BookEntry

_MODEL = "llama3.1:8b"

_OUTLINE_SYSTEM = """You are a professional novelist. You create tight, purposeful chapter outlines.
Each chapter outline specifies: what happens, whose POV, the emotional beat, and how it ends.
Return ONLY a JSON array of chapter objects. No preamble."""

_CHAPTER_SYSTEM = """You are a professional novelist writing in the specified genre and style.
Write the full chapter exactly as it would appear in the published book.
No meta-commentary. No chapter summaries. Just the chapter text itself.
Write approximately {word_count} words. Start with the chapter title on its own line."""


@dataclass
class ChapterOutline:
    number: int
    title: str
    pov: str
    summary: str
    emotional_beat: str
    chapter_end_hook: str


def generate_chapter_outlines(
    series: SeriesBible,
    book: BookEntry,
    genre_def: GenreDef,
    model: str = _MODEL,
) -> list[ChapterOutline]:
    """Generate chapter-by-chapter outline for one book."""
    prompt = (
        f"Series: {series.series_title}\n"
        f"Book #{book.number}: {book.title}\n"
        f"Protagonist: {book.protagonist}\n"
        f"Core trope: {book.trope}\n"
        f"Logline: {book.logline}\n"
        f"Conflict: {book.conflict}\n"
        f"Resolution: {book.resolution_hint}\n"
        f"Setting: {series.setting}\n"
        f"World: {series.world_description}\n\n"
        f"Generate a {genre_def.chapters_per_book}-chapter outline for this book. "
        f"Each chapter should advance plot AND character. "
        f"The emotional arc should escalate to a dark moment around chapter {genre_def.chapters_per_book - 4} "
        f"and resolve satisfyingly in the final chapters.\n\n"
        f"Return a JSON array:\n"
        f'[{{"number": 1, "title": "Chapter Title", "pov": "Character Name", '
        f'"summary": "What happens", "emotional_beat": "How it feels", '
        f'"chapter_end_hook": "What pulls the reader to next chapter"}}]'
    )
    raw = ollama.call_json(prompt, system=_OUTLINE_SYSTEM, model=model,
                           temperature=0.8, max_tokens=4000)
    chapters = raw if isinstance(raw, list) else []
    return [
        ChapterOutline(
            number=c.get("number", i + 1),
            title=c.get("title", f"Chapter {i+1}"),
            pov=c.get("pov", book.protagonist),
            summary=c.get("summary", ""),
            emotional_beat=c.get("emotional_beat", ""),
            chapter_end_hook=c.get("chapter_end_hook", ""),
        )
        for i, c in enumerate(chapters)
    ]


def write_chapter(
    series: SeriesBible,
    book: BookEntry,
    outline: ChapterOutline,
    genre_def: GenreDef,
    prior_summaries: list[str],
    model: str = _MODEL,
) -> str:
    """Write a full chapter given its outline. Returns chapter text."""
    prior_ctx = ""
    if prior_summaries:
        recent = prior_summaries[-3:]
        prior_ctx = f"Previous chapters summary:\n" + "\n".join(f"- {s}" for s in recent) + "\n\n"

    cast_desc = "\n".join(
        f"- {c['name']}: {c['description']}"
        for c in series.recurring_cast[:6]
    )

    prompt = (
        f"SERIES: {series.series_title} | BOOK #{book.number}: {book.title}\n"
        f"GENRE: {genre_def.name} | STYLE: {genre_def.chapter_style}\n\n"
        f"RECURRING CAST:\n{cast_desc}\n\n"
        f"SETTING: {series.setting}\n"
        f"{prior_ctx}"
        f"NOW WRITE CHAPTER {outline.number}: {outline.title}\n"
        f"POV: {outline.pov}\n"
        f"What happens: {outline.summary}\n"
        f"Emotional beat: {outline.emotional_beat}\n"
        f"End hook: {outline.chapter_end_hook}\n\n"
        f"Write the full chapter. Approximately {genre_def.words_per_chapter} words. "
        f"Start with 'Chapter {outline.number}: {outline.title}' on its own line."
    )

    system = _CHAPTER_SYSTEM.format(word_count=genre_def.words_per_chapter)
    return ollama.call(prompt, system=system, model=model,
                       temperature=0.85, max_tokens=5000)


def summarize_chapter(chapter_text: str, model: str = _MODEL) -> str:
    """Create a short summary of a chapter for context in subsequent chapters."""
    prompt = (
        f"Summarize this chapter in 2 sentences for use as context when writing the next chapter. "
        f"Focus on: what happened, how the relationship/situation changed, emotional state.\n\n"
        f"{chapter_text[:3000]}"
    )
    return ollama.call(prompt, model=model, temperature=0.3, max_tokens=200)


def write_book(
    series: SeriesBible,
    book: BookEntry,
    genre_def: GenreDef,
    output_dir: Path,
    model: str = _MODEL,
    log_fn=print,
) -> Path:
    """
    Write all chapters of one book. Resumes from last completed chapter.
    Returns path to the chapters directory.
    """
    book_dir = output_dir / f"book_{book.number:02d}"
    book_dir.mkdir(parents=True, exist_ok=True)
    outline_path = book_dir / "outline.json"
    summaries_path = book_dir / "summaries.json"

    # Generate or load outline
    if outline_path.exists():
        log_fn(f"    Loading existing outline...")
        raw = json.loads(outline_path.read_text())
        outlines = [ChapterOutline(**c) for c in raw]
    else:
        log_fn(f"    Generating chapter outline ({genre_def.chapters_per_book} chapters)...")
        outlines = generate_chapter_outlines(series, book, genre_def, model)
        outline_path.write_text(json.dumps(
            [{"number": o.number, "title": o.title, "pov": o.pov,
              "summary": o.summary, "emotional_beat": o.emotional_beat,
              "chapter_end_hook": o.chapter_end_hook} for o in outlines],
            indent=2
        ))

    # Load existing summaries
    summaries = json.loads(summaries_path.read_text()) if summaries_path.exists() else []

    # Write each chapter (skip already written)
    for outline in outlines:
        chapter_path = book_dir / f"chapter_{outline.number:02d}.txt"
        if chapter_path.exists():
            log_fn(f"    Chapter {outline.number} already exists, skipping...")
            if len(summaries) < outline.number:
                summary = summarize_chapter(chapter_path.read_text(), model)
                summaries.append(summary)
                summaries_path.write_text(json.dumps(summaries, indent=2))
            continue

        log_fn(f"    Writing chapter {outline.number}/{len(outlines)}: {outline.title}...")
        text = write_chapter(series, book, outline, genre_def, summaries, model)
        chapter_path.write_text(text, encoding="utf-8")

        summary = summarize_chapter(text, model)
        summaries.append(summary)
        summaries_path.write_text(json.dumps(summaries, indent=2))
        log_fn(f"      ✓ {len(text.split())} words")

    return book_dir
