"""
EPUB builder — assembles all chapters into a publishable EPUB file.
"""
from __future__ import annotations

import re
from pathlib import Path
from datetime import datetime

from ebooklib import epub


def build_epub(
    series_title: str,
    book_title: str,
    book_number: int,
    author: str,
    genre: str,
    book_dir: Path,
    output_path: Path | None = None,
) -> Path:
    """
    Build an EPUB from chapter files in book_dir.
    Chapter files: chapter_01.txt, chapter_02.txt, ...
    """
    chapter_files = sorted(book_dir.glob("chapter_*.txt"))
    if not chapter_files:
        raise FileNotFoundError(f"No chapter files found in {book_dir}")

    book = epub.EpubBook()
    book.set_identifier(f"{series_title}-{book_number}-{datetime.now().strftime('%Y%m%d')}")
    book.set_title(book_title)
    book.set_language("en")
    book.add_author(author)
    book.add_metadata("DC", "series", series_title)
    book.add_metadata("DC", "description", f"Book {book_number} of the {series_title} series. Genre: {genre}.")

    chapters = []
    toc = []
    spine = ["nav"]

    for i, ch_path in enumerate(chapter_files, 1):
        raw = ch_path.read_text(encoding="utf-8")
        lines = raw.strip().split("\n")

        # Extract chapter title from first line
        title_line = lines[0] if lines else f"Chapter {i}"
        body_lines = lines[1:] if len(lines) > 1 else []
        body_text = "\n".join(body_lines).strip()

        # Convert plain text to HTML paragraphs
        paragraphs = []
        for para in body_text.split("\n\n"):
            para = para.strip()
            if para:
                escaped = para.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                paragraphs.append(f"<p>{escaped}</p>")

        html_content = (
            f"<?xml version='1.0' encoding='utf-8'?>"
            f"<html xmlns='http://www.w3.org/1999/xhtml'>"
            f"<head><title>{title_line}</title></head>"
            f"<body>"
            f"<h1>{title_line}</h1>"
            + "".join(paragraphs) +
            f"</body></html>"
        )

        ch_file_name = f"chapter_{i:02d}.xhtml"
        epub_chapter = epub.EpubHtml(title=title_line, file_name=ch_file_name, lang="en")
        epub_chapter.set_content(html_content.encode("utf-8"))

        book.add_item(epub_chapter)
        chapters.append(epub_chapter)
        toc.append(epub.Link(ch_file_name, title_line, f"chapter{i}"))
        spine.append(epub_chapter)

    book.toc = toc
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = spine

    if output_path is None:
        safe = re.sub(r"[^\w\s-]", "", book_title).strip().replace(" ", "_")[:50]
        output_path = book_dir / f"{safe}.epub"

    epub.write_epub(str(output_path), book, {})
    return output_path
