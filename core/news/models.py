from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class RawArticle:
    title: str
    url: str
    source: str
    published: datetime | None
    summary: str = ""
    full_text: str = ""
    category: str = "general"


@dataclass
class CaptionLine:
    index: int
    start_ms: int
    end_ms: int
    text: str

    def to_srt(self) -> str:
        def _fmt(ms: int) -> str:
            h, rem = divmod(ms, 3_600_000)
            m, rem = divmod(rem, 60_000)
            s, ms_ = divmod(rem, 1_000)
            return f"{h:02}:{m:02}:{s:02},{ms_:03}"
        return f"{self.index}\n{_fmt(self.start_ms)} --> {_fmt(self.end_ms)}\n{self.text}"


@dataclass
class ProcessedScript:
    headline: str
    anchor_script: str          # full spoken text, cleaned
    sentences: list[str]        # list of individual broadcast sentences
    captions: list[CaptionLine] # SRT-ready caption objects
    srt: str                    # full SRT string
    word_count: int
    estimated_duration_sec: float
    source_url: str
    source_name: str
    original_title: str
