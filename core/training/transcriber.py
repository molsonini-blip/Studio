from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from core.training.scraper import DownloadedClip


@dataclass
class TranscriptSegment:
    start_sec: float
    end_sec: float
    text: str


@dataclass
class Transcript:
    item_id: str
    source: str          # "caption" | "whisper"
    segments: list[TranscriptSegment]
    full_text: str = ""

    def __post_init__(self):
        if not self.full_text:
            self.full_text = " ".join(s.text.strip() for s in self.segments)


# ── SRT parsing ───────────────────────────────────────────────────────────────

def _parse_srt_time(t: str) -> float:
    """Convert SRT timestamp HH:MM:SS,mmm to seconds."""
    h, m, rest = t.strip().split(":")
    s, ms = rest.replace(",", ".").split(".")
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def parse_srt(path: Path) -> list[TranscriptSegment]:
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    blocks = re.split(r'\n\s*\n', text.strip())
    segments = []
    for block in blocks:
        lines = [l.strip() for l in block.strip().splitlines() if l.strip()]
        if len(lines) < 3:
            continue
        try:
            start_str, end_str = lines[1].split(" --> ")
            start = _parse_srt_time(start_str)
            end = _parse_srt_time(end_str)
            caption_text = " ".join(lines[2:])
            # Strip HTML tags and music/sound effect markers
            caption_text = re.sub(r'<[^>]+>', '', caption_text)
            caption_text = re.sub(r'\[.*?\]|\(.*?\)', '', caption_text)
            caption_text = caption_text.strip()
            if caption_text:
                segments.append(TranscriptSegment(start_sec=start, end_sec=end, text=caption_text))
        except Exception:
            continue
    return segments


# ── Whisper transcription ──────────────────────────────────────────────────────

def transcribe_whisper(audio_path: Path, model_size: str = "base") -> list[TranscriptSegment]:
    """Transcribe audio using faster-whisper (CPU-optimised)."""
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise ImportError("faster-whisper not installed. Run: pip install faster-whisper")

    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    segments_iter, _ = model.transcribe(str(audio_path), beam_size=5, language="en")

    segments = []
    for seg in segments_iter:
        text = seg.text.strip()
        if text:
            segments.append(TranscriptSegment(
                start_sec=seg.start,
                end_sec=seg.end,
                text=text,
            ))
    return segments


# ── Main entry ────────────────────────────────────────────────────────────────

def transcribe_clip(clip: DownloadedClip, whisper_model: str = "base") -> Transcript | None:
    """Return a Transcript for a clip — uses captions if present, else Whisper."""
    if clip.has_captions and clip.caption_path and clip.caption_path.exists():
        segments = parse_srt(clip.caption_path)
        if segments:
            return Transcript(item_id=clip.item_id, source="caption", segments=segments)

    if clip.audio_path and clip.audio_path.exists():
        print(f"  [whisper] transcribing {clip.item_id} ...")
        segments = transcribe_whisper(clip.audio_path, model_size=whisper_model)
        return Transcript(item_id=clip.item_id, source="whisper", segments=segments)

    return None


def transcribe_all(
    clips: list[DownloadedClip],
    whisper_model: str = "base",
) -> list[Transcript]:
    transcripts = []
    for clip in clips:
        t = transcribe_clip(clip, whisper_model)
        if t:
            transcripts.append(t)
            print(f"  transcribed {clip.item_id} ({t.source}, {len(t.segments)} segments)")
    return transcripts
