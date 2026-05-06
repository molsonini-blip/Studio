from __future__ import annotations

import re

from core.news.models import CaptionLine, ProcessedScript

# Broadcast standard: ~130 words per minute anchor delivery pace
_WORDS_PER_MINUTE = 130
# Max characters per caption line (broadcast standard)
_MAX_CAPTION_CHARS = 42
# Ms per caption line (approx 1.5 words/sec = ~2.5s for a short line)
_MS_PER_WORD = int(60_000 / _WORDS_PER_MINUTE)


def _split_sentences(text: str) -> list[str]:
    """Split text into broadcast-ready sentences."""
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    # Split on sentence-ending punctuation
    raw = re.split(r'(?<=[.!?])\s+', text)
    sentences = []
    for s in raw:
        s = s.strip()
        if not s:
            continue
        # Break very long sentences at commas if over ~20 words
        words = s.split()
        if len(words) > 20:
            parts = re.split(r',\s+', s)
            for part in parts:
                if part.strip():
                    sentences.append(part.strip())
        else:
            sentences.append(s)
    return sentences


def _wrap_caption_line(text: str) -> list[str]:
    """Wrap a sentence into ≤42-char caption lines."""
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = (current + " " + word).strip()
        if len(candidate) <= _MAX_CAPTION_CHARS:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _build_srt(captions: list[CaptionLine]) -> str:
    return "\n\n".join(c.to_srt() for c in captions)


def build_script(
    headline: str,
    anchor_text: str,
    source_url: str,
    source_name: str,
    original_title: str,
    words_per_minute: int = _WORDS_PER_MINUTE,
) -> ProcessedScript:
    sentences = _split_sentences(anchor_text)
    ms_per_word = int(60_000 / words_per_minute)

    captions: list[CaptionLine] = []
    cursor_ms = 0
    idx = 1

    for sentence in sentences:
        wrapped = _wrap_caption_line(sentence)
        for line in wrapped:
            word_count = len(line.split())
            duration_ms = max(word_count * ms_per_word, 1500)  # min 1.5s per line
            captions.append(CaptionLine(
                index=idx,
                start_ms=cursor_ms,
                end_ms=cursor_ms + duration_ms,
                text=line,
            ))
            cursor_ms += duration_ms
            idx += 1

    total_words = len(anchor_text.split())
    duration_sec = (total_words / words_per_minute) * 60

    return ProcessedScript(
        headline=headline,
        anchor_script=anchor_text,
        sentences=sentences,
        captions=captions,
        srt=_build_srt(captions),
        word_count=total_words,
        estimated_duration_sec=round(duration_sec, 1),
        source_url=source_url,
        source_name=source_name,
        original_title=original_title,
    )
