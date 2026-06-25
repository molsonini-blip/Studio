#!/usr/bin/env python3
"""
Romance series idea generator — powered by Ollama.

Generates dime-store romance series concepts: 20-book arcs,
individual book synopses, and character sheets.

Usage:
  # Generate a new 20-book series concept:
  python -m books.romance.ideas --series --theme "small-town firefighters"

  # Generate 5 standalone book ideas in a genre flavor:
  python -m books.romance.ideas --books 5 --flavor "billionaire CEO"

  # Generate character profiles for a series:
  python -m books.romance.ideas --characters --series-file books/romance/series/my_series.json

  # Save new series to file:
  python -m books.romance.ideas --series --theme "Navy SEALs" --save navy_seals_series
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, asdict, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from shared import ollama

# ---------------------------------------------------------------------------
# Romance sub-flavors (dime-store / mass market)
# ---------------------------------------------------------------------------

FLAVORS = [
    "small-town sweet romance",
    "billionaire CEO romance",
    "cowboy / rancher romance",
    "military / Navy SEAL romance",
    "enemies to lovers",
    "second chance romance",
    "forbidden romance",
    "royal / duke romance",
    "shifter / paranormal romance",
    "sports romance",
    "fake dating / marriage of convenience",
    "single parent romance",
]

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class Character:
    name: str
    role: str           # "hero", "heroine", "villain", "best friend"
    age: int
    occupation: str
    backstory: str
    personality: str
    flaw: str
    goal: str

@dataclass
class BookSynopsis:
    book_number: int
    title: str
    tagline: str        # the one-liner on the cover
    hero: str
    heroine: str
    conflict: str       # the central obstacle to love
    hook: str           # the first-chapter inciting incident
    black_moment: str   # the dark night before the happy ending
    resolution: str
    heat_level: str     # "sweet", "steamy", "explicit"
    word_count_target: int

@dataclass
class SeriesConcept:
    series_title: str
    tagline: str
    flavor: str
    setting: str
    overarching_plot: str   # series-wide arc beyond individual HEAs
    recurring_cast: list[Character]
    books: list[BookSynopsis]
    total_books: int = 20
    reading_order_notes: str = ""


# ---------------------------------------------------------------------------
# Ollama prompts
# ---------------------------------------------------------------------------

_SERIES_SYSTEM = """You are a romance novelist who has written dozens of successful mass-market romance series.
You know exactly what readers want: fast hooks, strong chemistry, satisfying HEAs, and a world they want to live in.

RULES:
1. Every book must have a distinct hero and heroine but share a world and recurring cast.
2. The series arc gives readers a reason to keep buying — a mystery, a family saga, a community event.
3. Taglines must sound like real cover copy. Punchy. Emotional. Specific.
4. Heat levels vary across the series to reach different readers.
5. Return ONLY valid JSON. No preamble.

JSON schema:
{
  "series_title": "...",
  "tagline": "series-level one-liner",
  "flavor": "romance sub-genre",
  "setting": "specific place and time",
  "overarching_plot": "what ties all 20 books together beyond individual love stories",
  "reading_order_notes": "standalone or must-read-in-order?",
  "recurring_cast": [
    {"name": "...", "role": "...", "age": 0, "occupation": "...", "backstory": "...", "personality": "...", "flaw": "...", "goal": "..."}
  ],
  "books": [
    {
      "book_number": 1,
      "title": "...",
      "tagline": "...",
      "hero": "name + brief description",
      "heroine": "name + brief description",
      "conflict": "...",
      "hook": "...",
      "black_moment": "...",
      "resolution": "...",
      "heat_level": "sweet|steamy|explicit",
      "word_count_target": 60000
    }
  ]
}"""

_BOOKS_SYSTEM = """You are a romance novel packager. Generate individual romance book concepts —
each a complete, compelling read with real emotional stakes.

Return ONLY a JSON array. No preamble.

Schema per book:
{
  "book_number": 1,
  "title": "...",
  "tagline": "...",
  "hero": "...",
  "heroine": "...",
  "conflict": "...",
  "hook": "...",
  "black_moment": "...",
  "resolution": "...",
  "heat_level": "sweet|steamy|explicit",
  "word_count_target": 60000
}"""


def _series_prompt(theme: str, book_count: int) -> str:
    return (
        f"Create a {book_count}-book mass-market romance series.\n"
        f"Theme/world: {theme}\n\n"
        f"Requirements:\n"
        f"- Each book follows a different couple but shares the same world and recurring cast.\n"
        f"- Books should be mostly standalone with a light series arc.\n"
        f"- Mix heat levels (sweet, steamy, explicit) across the series.\n"
        f"- The overarching plot gives readers a reason to read all {book_count} books.\n"
        f"- Include {min(6, book_count // 3)} recurring cast members who appear throughout.\n"
        f"- Generate all {book_count} book entries in the 'books' array."
    )


def _books_prompt(flavor: str, count: int) -> str:
    return (
        f"Generate {count} standalone romance novels in the '{flavor}' style.\n"
        f"Each should be a complete, emotionally satisfying story.\n"
        f"Vary the heat levels and conflict types across the {count} books."
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_series(
    theme: str,
    book_count: int = 20,
    model: str = ollama._DEFAULT_MODEL,
) -> SeriesConcept:
    """Generate a complete romance series concept."""
    raw = ollama.call_json(
        _series_prompt(theme, book_count),
        system=_SERIES_SYSTEM,
        model=model,
        temperature=0.9,
        max_tokens=6000,
    )
    cast = [
        Character(
            name=c.get("name", ""),
            role=c.get("role", ""),
            age=c.get("age", 30),
            occupation=c.get("occupation", ""),
            backstory=c.get("backstory", ""),
            personality=c.get("personality", ""),
            flaw=c.get("flaw", ""),
            goal=c.get("goal", ""),
        )
        for c in raw.get("recurring_cast", [])
    ]
    books = [
        BookSynopsis(
            book_number=b.get("book_number", i + 1),
            title=b.get("title", f"Book {i+1}"),
            tagline=b.get("tagline", ""),
            hero=b.get("hero", ""),
            heroine=b.get("heroine", ""),
            conflict=b.get("conflict", ""),
            hook=b.get("hook", ""),
            black_moment=b.get("black_moment", ""),
            resolution=b.get("resolution", ""),
            heat_level=b.get("heat_level", "steamy"),
            word_count_target=b.get("word_count_target", 60000),
        )
        for i, b in enumerate(raw.get("books", []))
    ]
    return SeriesConcept(
        series_title=raw.get("series_title", "Untitled Series"),
        tagline=raw.get("tagline", ""),
        flavor=raw.get("flavor", theme),
        setting=raw.get("setting", ""),
        overarching_plot=raw.get("overarching_plot", ""),
        recurring_cast=cast,
        books=books,
        total_books=book_count,
        reading_order_notes=raw.get("reading_order_notes", ""),
    )


def generate_books(
    flavor: str,
    count: int = 5,
    model: str = ollama._DEFAULT_MODEL,
) -> list[BookSynopsis]:
    """Generate standalone romance book concepts."""
    raw = ollama.call_json(
        _books_prompt(flavor, count),
        system=_BOOKS_SYSTEM,
        model=model,
        temperature=0.9,
        max_tokens=4000,
    )
    books_raw = raw if isinstance(raw, list) else raw.get("books", [])
    return [
        BookSynopsis(
            book_number=b.get("book_number", i + 1),
            title=b.get("title", f"Book {i+1}"),
            tagline=b.get("tagline", ""),
            hero=b.get("hero", ""),
            heroine=b.get("heroine", ""),
            conflict=b.get("conflict", ""),
            hook=b.get("hook", ""),
            black_moment=b.get("black_moment", ""),
            resolution=b.get("resolution", ""),
            heat_level=b.get("heat_level", "steamy"),
            word_count_target=b.get("word_count_target", 60000),
        )
        for i, b in enumerate(books_raw)
    ]


def save_series(series: SeriesConcept, name: str) -> Path:
    out_dir = Path(__file__).parent / "series"
    out_dir.mkdir(exist_ok=True)
    out = out_dir / f"{name}.json"
    out.write_text(json.dumps(asdict(series), indent=2))
    return out


def print_series_summary(series: SeriesConcept) -> None:
    print(f"\n{'='*60}")
    print(f"SERIES: {series.series_title}")
    print(f"        {series.tagline}")
    print(f"Flavor: {series.flavor}")
    print(f"Setting: {series.setting}")
    print(f"Arc:    {series.overarching_plot}")
    print(f"Order:  {series.reading_order_notes}")
    print(f"\nRecurring Cast ({len(series.recurring_cast)}):")
    for c in series.recurring_cast:
        print(f"  • {c.name} ({c.role}, {c.age}) — {c.occupation}: {c.backstory[:80]}...")
    print(f"\nBooks ({len(series.books)}):")
    for b in series.books:
        print(f"  [{b.book_number:2d}] {b.title} [{b.heat_level}]")
        print(f"       {b.tagline}")
        print(f"       Hero: {b.hero} | Heroine: {b.heroine}")
        print(f"       Conflict: {b.conflict[:80]}...")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate romance book/series ideas")
    parser.add_argument("--series", action="store_true",
                        help="Generate a full multi-book series")
    parser.add_argument("--theme", default="small-town second chances",
                        help="Series theme or world concept")
    parser.add_argument("--book-count", type=int, default=20,
                        help="Number of books in the series (default: 20)")
    parser.add_argument("--books", type=int, default=0,
                        help="Generate N standalone book concepts instead")
    parser.add_argument("--flavor", default="small-town sweet romance",
                        choices=FLAVORS, help="Romance sub-genre flavor")
    parser.add_argument("--save", metavar="NAME",
                        help="Save series to books/romance/series/NAME.json")
    parser.add_argument("--list-flavors", action="store_true",
                        help="List romance flavor options and exit")
    parser.add_argument("--model", default=ollama._DEFAULT_MODEL)
    args = parser.parse_args()

    if args.list_flavors:
        print("Romance flavors:")
        for f in FLAVORS:
            print(f"  • {f}")
        return

    if args.series or (not args.books):
        print(f"Generating {args.book_count}-book series: '{args.theme}' ...")
        series = generate_series(args.theme, book_count=args.book_count, model=args.model)
        print_series_summary(series)
        if args.save:
            path = save_series(series, args.save)
            print(f"\nSaved to {path}")
    else:
        print(f"Generating {args.books} standalone {args.flavor} books ...")
        books = generate_books(args.flavor, count=args.books, model=args.model)
        for b in books:
            print(f"\n[{b.book_number}] {b.title.upper()} [{b.heat_level}]")
            print(f"  {b.tagline}")
            print(f"  Hero: {b.hero}")
            print(f"  Heroine: {b.heroine}")
            print(f"  Conflict: {b.conflict}")
            print(f"  Hook: {b.hook}")


if __name__ == "__main__":
    main()
