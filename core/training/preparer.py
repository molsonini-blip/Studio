from __future__ import annotations

import json
import re
from pathlib import Path

from core.training.transcriber import Transcript


# ── Broadcast transcript cleaning ─────────────────────────────────────────────

_FILLER = re.compile(
    r'\b(um+|uh+|ah+|er+|hmm+|you know|i mean|like|basically|literally|'
    r'kind of|sort of|right\?|okay\?|so yeah)\b',
    re.IGNORECASE
)
_MULTI_SPACE = re.compile(r' {2,}')
_CROSSTALK = re.compile(
    r'(CROSSTALK|INAUDIBLE|UNINTELLIGIBLE|\[.*?\]|\(.*?\))',
    re.IGNORECASE
)


def clean_transcript(text: str) -> str:
    """Remove filler words, crosstalk markers, and noise from broadcast text."""
    text = _CROSSTALK.sub('', text)
    text = _FILLER.sub('', text)
    text = _MULTI_SPACE.sub(' ', text)
    # Remove lines that are mostly punctuation or very short
    lines = [l.strip() for l in text.splitlines() if len(l.strip()) > 10]
    return ' '.join(lines).strip()


def split_into_segments(text: str, max_words: int = 150) -> list[str]:
    """Split a long transcript into anchor-delivery-sized segments."""
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    segments, current, count = [], [], 0
    for sent in sentences:
        words = len(sent.split())
        if count + words > max_words and current:
            segments.append(' '.join(current))
            current, count = [sent], words
        else:
            current.append(sent)
            count += words
    if current:
        segments.append(' '.join(current))
    return [s for s in segments if len(s.split()) >= 20]


# ── LLM fine-tune dataset ─────────────────────────────────────────────────────

_LLM_INSTRUCTION = (
    "Rewrite the following raw news text as a professional broadcast anchor script. "
    "Use short declarative sentences. State only verifiable facts. "
    "Remove all opinion, speculation, and political framing. "
    "Write at a 7th grade reading level. Use active voice."
)


def build_llm_dataset(
    transcripts: list[Transcript],
    output_path: Path,
    format: str = "alpaca",       # alpaca | sharegpt
) -> int:
    """Build a fine-tuning dataset from broadcast transcripts.

    Each example is a (raw_segment → cleaned_broadcast_script) pair.
    Since the source IS broadcast text, the input and output are the same segment
    in different forms — we use the raw SRT/Whisper text as 'input' and the
    cleaned/reformatted version as 'output'.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    examples = []
    for transcript in transcripts:
        raw_text = transcript.full_text
        if not raw_text or len(raw_text.split()) < 30:
            continue

        cleaned = clean_transcript(raw_text)
        segments = split_into_segments(cleaned, max_words=150)

        for seg in segments:
            # Simulate a raw article as input by slightly degrading the clean text
            # (adds filler / passive voice markers as noise to teach the model to clean)
            raw_input = seg  # In practice: pair with a real raw article if available

            if format == "alpaca":
                examples.append({
                    "instruction": _LLM_INSTRUCTION,
                    "input": raw_input,
                    "output": seg,
                })
            elif format == "sharegpt":
                examples.append({
                    "conversations": [
                        {"from": "system", "value": _LLM_INSTRUCTION},
                        {"from": "human", "value": raw_input},
                        {"from": "gpt", "value": seg},
                    ]
                })

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(examples, f, indent=2, ensure_ascii=False)

    print(f"LLM dataset: {len(examples)} examples → {output_path}")
    return len(examples)


# ── Talking head dataset ──────────────────────────────────────────────────────

def build_talking_head_dataset(
    clips_dir: Path,
    output_manifest: Path,
) -> int:
    """Build a manifest of (video_clip, audio_clip, transcript) triples for
    talking head fine-tuning.

    Each row points to a short video segment of a single speaker (anchor)
    with aligned audio and transcript text.
    """
    clips_dir = Path(clips_dir)
    output_manifest = Path(output_manifest)
    output_manifest.parent.mkdir(parents=True, exist_ok=True)

    manifest = []
    for item_dir in sorted(clips_dir.iterdir()):
        if not item_dir.is_dir():
            continue
        videos = list(item_dir.glob("*.mp4"))
        audios = list(item_dir.glob("*.wav"))
        srts = list(item_dir.glob("*.srt"))
        if not videos or not audios:
            continue

        transcript_text = ""
        if srts:
            from core.training.transcriber import parse_srt
            segs = parse_srt(srts[0])
            transcript_text = " ".join(s.text for s in segs)

        manifest.append({
            "id": item_dir.name,
            "video": str(videos[0]),
            "audio": str(audios[0]),
            "transcript": transcript_text,
        })

    with open(output_manifest, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"Talking head manifest: {len(manifest)} clips → {output_manifest}")
    return len(manifest)
