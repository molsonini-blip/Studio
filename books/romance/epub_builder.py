#!/usr/bin/env python3
"""
EPUB / PDF builder — assembles generated chapters into a distributable file.

Requires: pip install ebooklib Pillow reportlab (for PDF)

Usage:
  # Build EPUB from generated chapters:
  python -m books.romance.epub_builder \
    --series books/romance/series/navy_seals.json --book 1

  # Build PDF instead:
  python -m books.romance.epub_builder \
    --series books/romance/series/navy_seals.json --book 1 --format pdf

  # Custom cover image:
  python -m books.romance.epub_builder \
    --series books/romance/series/navy_seals.json --book 1 --cover my_cover.jpg

  # Build all books in a series:
  python -m books.romance.epub_builder \
    --series books/romance/series/navy_seals.json --all
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from books.romance.ideas import BookSynopsis, SeriesConcept
from books.romance.chapter_generator import get_output_dir

OUTPUT_DIR = Path(__file__).parent / "output"


def _load_chapters(book_dir: Path) -> list[tuple[int, str, str]]:
    """Return list of (chapter_num, title, text) sorted by chapter number."""
    outline_path = book_dir / "outline.json"
    outline = {}
    if outline_path.exists():
        for ch in json.loads(outline_path.read_text()):
            outline[ch.get("chapter", 0)] = ch.get("title", "")

    chapters = []
    for ch_file in sorted(book_dir.glob("chapter_??.txt")):
        m = re.search(r"chapter_(\d+)\.txt", ch_file.name)
        if not m:
            continue
        num = int(m.group(1))
        text = ch_file.read_text(encoding="utf-8")
        title = outline.get(num, f"Chapter {num}")
        chapters.append((num, title, text))
    return sorted(chapters)


def build_epub(book: BookSynopsis, series_name: str, cover_path: Path | None = None) -> Path:
    """Assemble an EPUB from generated chapter files."""
    try:
        from ebooklib import epub
    except ImportError:
        print("Install ebooklib: pip install ebooklib")
        sys.exit(1)

    book_dir = get_output_dir(series_name, book.book_number)
    chapters = _load_chapters(book_dir)
    if not chapters:
        print(f"No chapters found in {book_dir}")
        sys.exit(1)

    ebook = epub.EpubBook()
    ebook.set_identifier(f"{series_name}_book{book.book_number}")
    ebook.set_title(book.title)
    ebook.set_language("en")
    ebook.add_metadata("DC", "description", book.tagline)

    if cover_path and cover_path.exists():
        ebook.set_cover("cover.jpg", cover_path.read_bytes())

    css = epub.EpubItem(
        uid="style",
        file_name="style.css",
        media_type="text/css",
        content=b"body { font-family: Georgia, serif; line-height: 1.6; } h1 { text-align: center; }",
    )
    ebook.add_item(css)

    spine = ["nav"]
    epub_chapters = []
    for num, title, text in chapters:
        ch = epub.EpubHtml(title=title, file_name=f"chapter_{num:02d}.xhtml", lang="en")
        html_text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        paragraphs = "".join(f"<p>{p.strip()}</p>" for p in html_text.split("\n\n") if p.strip())
        ch.content = f"<html><body><h1>{title}</h1>{paragraphs}</body></html>"
        ch.add_link(href="style.css", rel="stylesheet", type="text/css")
        ebook.add_item(ch)
        epub_chapters.append(ch)
        spine.append(ch)

    ebook.toc = tuple(epub_chapters)
    ebook.spine = spine
    ebook.add_item(epub.EpubNcx())
    ebook.add_item(epub.EpubNav())

    out_path = book_dir / f"{book.title.replace(' ', '_')}.epub"
    epub.write_epub(str(out_path), ebook)
    return out_path


def build_pdf(book: BookSynopsis, series_name: str, cover_path: Path | None = None) -> Path:
    """Assemble a PDF from generated chapter files."""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
        from reportlab.lib import colors
    except ImportError:
        print("Install reportlab: pip install reportlab")
        sys.exit(1)

    book_dir = get_output_dir(series_name, book.book_number)
    chapters = _load_chapters(book_dir)
    if not chapters:
        print(f"No chapters found in {book_dir}")
        sys.exit(1)

    out_path = book_dir / f"{book.title.replace(' ', '_')}.pdf"
    doc = SimpleDocTemplate(str(out_path), pagesize=letter,
                            rightMargin=inch, leftMargin=inch,
                            topMargin=inch, bottomMargin=inch)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("Title", parent=styles["Heading1"],
                                 fontSize=18, spaceAfter=12, alignment=1)
    chapter_style = ParagraphStyle("Chapter", parent=styles["Heading2"],
                                   fontSize=14, spaceAfter=10)
    body_style = ParagraphStyle("Body", parent=styles["Normal"],
                                fontSize=11, leading=16, spaceAfter=8)

    story = []
    # Title page
    story.append(Spacer(1, 2 * inch))
    story.append(Paragraph(book.title, title_style))
    story.append(Paragraph(book.tagline, styles["Italic"]))
    story.append(PageBreak())

    for num, title, text in chapters:
        story.append(Paragraph(title, chapter_style))
        for para in text.split("\n\n"):
            para = para.strip()
            if para:
                story.append(Paragraph(para, body_style))
        story.append(PageBreak())

    doc.build(story)
    return out_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Build EPUB or PDF from generated chapters")
    parser.add_argument("--series", required=True, help="Path to series JSON")
    parser.add_argument("--book", type=int, default=1, help="Book number (default: 1)")
    parser.add_argument("--all", action="store_true", help="Build all books in series")
    parser.add_argument("--format", choices=["epub", "pdf"], default="epub")
    parser.add_argument("--cover", help="Path to cover image")
    args = parser.parse_args()

    series_data = json.loads(Path(args.series).read_text())
    series_name = Path(args.series).stem
    books_raw = series_data.get("books", [])
    cover = Path(args.cover) if args.cover else None

    targets = books_raw if args.all else [b for b in books_raw if b["book_number"] == args.book]
    if not targets:
        print(f"Book {args.book} not found.")
        sys.exit(1)

    for b_raw in targets:
        book = BookSynopsis(**b_raw)
        print(f"Building {args.format.upper()}: {book.title} ...")
        if args.format == "epub":
            out = build_epub(book, series_name, cover)
        else:
            out = build_pdf(book, series_name, cover)
        print(f"  → {out}")


if __name__ == "__main__":
    main()
