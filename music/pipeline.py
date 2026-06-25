#!/usr/bin/env python3
"""
Music production pipeline.

Primary backend: MusicGen via HuggingFace transformers — runs on EdgeExpert GB10 GPU.
Fallback: Suno API (cloud, per-track cost).

Workflow:
  1. ideas.py generates SongIdeas via Ollama
  2. Pipeline builds a text prompt from each idea
  3. MusicGen generates audio on EdgeExpert's GPU (free, no API)
  4. Output: MP3 + metadata saved to music/genres/<genre>/

Usage (run on EdgeExpert):
  PYTHONPATH=~/projects/studio venv/bin/python -m music.pipeline \
      --idea music/projects/film_noir/soundtrack.json --all

  Single track:
    python -m music.pipeline --idea music/projects/film_noir/soundtrack.json --index 0

  Dry run (no generation, just print prompts):
    python -m music.pipeline --dry-run --idea ...

  Longer tracks (default 30s):
    python -m music.pipeline --duration 60 --idea ...

  Better model (downloads ~3.3 GB first time):
    python -m music.pipeline --model facebook/musicgen-stereo-large --idea ...
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from music.ideas import SongIdea


class AudioBackend(Protocol):
    name: str

    def generate(self, idea: SongIdea, output_path: Path) -> Path: ...
    def is_available(self) -> bool: ...


# ---------------------------------------------------------------------------
# Placeholder backend
# ---------------------------------------------------------------------------

class PlaceholderBackend:
    name = "placeholder"

    def generate(self, idea: SongIdea, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        meta = output_path.with_suffix(".json")
        meta.write_text(json.dumps({
            "title": idea.title, "genre": idea.genre, "mood": idea.mood,
            "tempo": idea.tempo, "key": idea.key, "instruments": idea.instruments,
            "production_notes": idea.production_notes, "status": "pending",
        }, indent=2))
        print(f"  [placeholder] {idea.title} | {idea.genre} | {idea.mood}")
        return output_path

    def is_available(self) -> bool:
        return True


# ---------------------------------------------------------------------------
# LOCAL MusicGen — HuggingFace transformers on EdgeExpert GB10 GPU
# ---------------------------------------------------------------------------

class LocalMusicGenBackend:
    """
    Generates music using MusicGen directly on the EdgeExpert GB10 Grace Blackwell GPU.
    Uses HuggingFace transformers — no audiocraft dependency.
    Free per generation. Models auto-download to ~/.cache/huggingface/ on first use.

    Models (quality vs speed trade-off):
      facebook/musicgen-small         — fast, ~300 MB
      facebook/musicgen-medium        — balanced, ~1.5 GB
      facebook/musicgen-large         — best quality, ~3.3 GB (mono)
      facebook/musicgen-stereo-large  — stereo, best for production (default)
    """
    name = "local_musicgen"
    _DEFAULT_MODEL = "facebook/musicgen-stereo-large"
    _DEFAULT_DURATION = 30  # seconds

    def __init__(self, model: str = _DEFAULT_MODEL, duration: int = _DEFAULT_DURATION):
        self.model_name = model
        self.duration = duration
        self._model = None
        self._processor = None

    def _load(self):
        if self._model is not None:
            return
        import torch
        from transformers import AutoProcessor, MusicgenForConditionalGeneration

        print(f"  Loading {self.model_name}...")
        self._processor = AutoProcessor.from_pretrained(self.model_name)
        self._model = MusicgenForConditionalGeneration.from_pretrained(self.model_name)
        if torch.cuda.is_available():
            self._model = self._model.cuda()
            print(f"  Running on GPU: {torch.cuda.get_device_name(0)}")
        else:
            print("  Running on CPU (no CUDA detected)")

    def _build_prompt(self, idea: SongIdea) -> str:
        parts = [idea.genre, idea.mood]
        if idea.tempo:
            parts.append(idea.tempo)
        if idea.instruments:
            parts.append(", ".join(idea.instruments[:6]))
        if idea.production_notes:
            parts.append(idea.production_notes[:200])
        return ", ".join(p for p in parts if p)

    def _tokens_for_seconds(self, seconds: int) -> int:
        # MusicGen: ~50 tokens/second at 32kHz (musicgen-small/medium/large)
        # musicgen-stereo models also use ~50 tokens/second
        return int(seconds * 51.2)

    def generate(self, idea: SongIdea, output_path: Path) -> Path:
        import torch
        import numpy as np
        import scipy.io.wavfile as wav_io

        output_path.parent.mkdir(parents=True, exist_ok=True)
        self._load()

        prompt = self._build_prompt(idea)
        print(f"  Prompt: {prompt[:120]}...")

        inputs = self._processor(text=[prompt], padding=True, return_tensors="pt")
        if torch.cuda.is_available():
            inputs = {k: v.cuda() if hasattr(v, "cuda") else v for k, v in inputs.items()}

        max_tokens = self._tokens_for_seconds(self.duration)
        with torch.no_grad():
            audio_values = self._model.generate(**inputs, max_new_tokens=max_tokens)

        audio_np = audio_values[0].cpu().numpy()  # shape: [channels, samples]
        sample_rate = self._model.config.audio_encoder.sampling_rate

        wav_path = output_path.with_suffix(".wav")
        if audio_np.shape[0] == 1:
            wav_io.write(str(wav_path), sample_rate, audio_np[0].astype(np.float32))
        else:
            # stereo: scipy expects (samples, channels)
            wav_io.write(str(wav_path), sample_rate, audio_np.T.astype(np.float32))

        mp3_path = _wav_to_mp3(wav_path, output_path)

        mp3_path.with_suffix(".json").write_text(json.dumps({
            "title": idea.title, "genre": idea.genre, "mood": idea.mood,
            "tempo": idea.tempo, "key": idea.key, "instruments": idea.instruments,
            "prompt": prompt, "duration_s": self.duration,
            "sample_rate": sample_rate, "model": self.model_name,
            "backend": self.name,
        }, indent=2))
        print(f"  Saved: {mp3_path}")
        return mp3_path

    def is_available(self) -> bool:
        try:
            from transformers import MusicgenForConditionalGeneration  # noqa: F401
            return True
        except ImportError:
            return False


# ---------------------------------------------------------------------------
# Suno API backend
# ---------------------------------------------------------------------------

class SunoBackend:
    """
    Suno official API — full songs with vocals.
    Better for pop/rock with lyrics than pure instrumental.
    Requires: SUNO_API_KEY env var.
    """
    name = "suno"

    def generate(self, idea: SongIdea, output_path: Path) -> Path:
        import httpx, os
        api_key = os.environ.get("SUNO_API_KEY")
        if not api_key:
            raise RuntimeError("Set SUNO_API_KEY env var")
        prompt = f"{idea.genre}, {idea.mood}, {idea.production_notes[:200]}"
        resp = httpx.post(
            "https://api.suno.ai/v1/generate",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"prompt": prompt, "make_instrumental": True},
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()
        audio_url = data.get("audio_url") or data.get("clips", [{}])[0].get("audio_url")
        if audio_url:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(httpx.get(audio_url, timeout=60).content)
        return output_path

    def is_available(self) -> bool:
        import os
        return bool(os.environ.get("SUNO_API_KEY"))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _wav_to_mp3(wav_path: Path, mp3_path: Path) -> Path:
    import subprocess
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(wav_path), "-codec:a", "libmp3lame",
             "-qscale:a", "2", str(mp3_path)],
            capture_output=True, check=True,
        )
        wav_path.unlink(missing_ok=True)
        return mp3_path
    except (subprocess.CalledProcessError, FileNotFoundError):
        return wav_path.rename(wav_path.with_suffix(".wav"))


def get_backend(name: str = "auto") -> AudioBackend:
    if name == "auto":
        local = LocalMusicGenBackend()
        if local.is_available():
            return local
        suno = SunoBackend()
        if suno.is_available():
            return suno
        return PlaceholderBackend()
    return {
        "local_musicgen": LocalMusicGenBackend(),
        "suno": SunoBackend(),
        "placeholder": PlaceholderBackend(),
    }.get(name, PlaceholderBackend())


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

@dataclass
class PipelineResult:
    idea: SongIdea
    output_path: Path
    success: bool
    error: str = ""


def _output_path_for(idea: SongIdea, index: int) -> Path:
    genre_dir = (
        Path(__file__).parent / "genres"
        / idea.genre.replace(" ", "_").replace("/", "_")
    )
    genre_dir.mkdir(parents=True, exist_ok=True)
    safe = "".join(c if c.isalnum() or c in " _-" else "" for c in idea.title)
    safe = safe.strip().replace(" ", "_")[:40]
    return genre_dir / f"{index:03d}_{safe}.mp3"


def run(
    idea: SongIdea,
    index: int = 0,
    dry_run: bool = False,
    backend: AudioBackend | None = None,
) -> PipelineResult:
    active = backend or get_backend("auto")
    out = _output_path_for(idea, index)
    if dry_run:
        prompt = active._build_prompt(idea) if hasattr(active, "_build_prompt") else "N/A"
        print(f"  [dry-run] [{active.name}] {idea.title}")
        print(f"    Prompt: {prompt[:100]}")
        print(f"    Output: {out}")
        return PipelineResult(idea=idea, output_path=out, success=True)
    if not active.is_available():
        msg = f"Backend '{active.name}' not available. Install: pip install transformers scipy"
        print(f"  ERROR: {msg}")
        return PipelineResult(idea=idea, output_path=out, success=False, error=msg)
    try:
        final = active.generate(idea, out)
        return PipelineResult(idea=idea, output_path=final, success=True)
    except Exception as e:
        return PipelineResult(idea=idea, output_path=out, success=False, error=str(e))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Music production pipeline — runs on EdgeExpert GPU")
    parser.add_argument("--idea", required=True,
                        help="Path to songs JSON file from music/ideas.py")
    parser.add_argument("--index", type=int, default=0, help="Song index (0-based)")
    parser.add_argument("--all", action="store_true", help="Produce all songs")
    parser.add_argument("--dry-run", action="store_true", help="Print prompts without generating")
    parser.add_argument("--backend", choices=["auto", "local_musicgen", "suno", "placeholder"],
                        default="auto")
    parser.add_argument("--duration", type=int, default=30, help="Audio duration in seconds")
    parser.add_argument("--model", default="facebook/musicgen-stereo-large",
                        help="MusicGen model (default: musicgen-stereo-large)")
    args = parser.parse_args()

    data = json.loads(Path(args.idea).read_text())
    songs_raw = data["tracks"] if isinstance(data, dict) and "tracks" in data else data
    songs = [SongIdea(**s) for s in songs_raw]

    if args.backend in ("auto", "local_musicgen"):
        active_backend = LocalMusicGenBackend(model=args.model, duration=args.duration)
    else:
        active_backend = get_backend(args.backend)

    indices = list(range(len(songs))) if args.all else [args.index]
    print(f"Backend: {active_backend.name} | Model: {args.model} | Duration: {args.duration}s | Songs: {len(indices)}")

    for i in indices:
        song = songs[i]
        print(f"\n[{i + 1}/{len(indices)}] {song.title} ({song.genre})")
        result = run(song, index=i, dry_run=args.dry_run, backend=active_backend)
        if not result.success:
            print(f"  FAILED: {result.error}")


if __name__ == "__main__":
    main()
