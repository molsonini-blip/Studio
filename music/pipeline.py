#!/usr/bin/env python3
"""
Music production pipeline.

Primary backend: MusicGen (Meta AudioCraft) — runs directly on EdgeExpert GPU.
Fallback: Suno API (cloud, per-track cost).

Workflow:
  1. ideas.py generates a SongIdea (or load one from JSON)
  2. Pipeline builds a text prompt from the idea
  3. MusicGen generates the audio locally on EdgeExpert's GPU
  4. Output: MP3 + metadata saved to music/genres/<genre>/

Usage:
  python -m music.pipeline --idea music/projects/my_film/songs.json --index 0
  python -m music.pipeline --idea music/projects/my_film/songs.json --all
  python -m music.pipeline --dry-run --idea music/projects/my_film/songs.json
  python -m music.pipeline --backend suno --idea ...
  python -m music.pipeline --backend runpod --idea ...   # legacy RunPod path
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from music.ideas import SongIdea, GENRES


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
            "production_notes": idea.production_notes,
            "status": "pending_audio_backend",
        }, indent=2))
        print(f"  [placeholder] Would generate: {idea.title}")
        print(f"    Genre: {idea.genre} | Mood: {idea.mood} | Tempo: {idea.tempo}")
        print(f"    → Metadata saved: {meta}")
        return output_path

    def is_available(self) -> bool:
        return True


# ---------------------------------------------------------------------------
# LOCAL MusicGen backend — runs AudioCraft directly on EdgeExpert GPU
# ---------------------------------------------------------------------------

class LocalMusicGenBackend:
    """
    Runs Meta's MusicGen directly on the EdgeExpert GB10 Grace Blackwell GPU.
    No API key, no RunPod cost — completely free per generation.

    Install on EdgeExpert:
      cd ~/projects/studio
      venv/bin/pip install audiocraft

    Models (auto-downloaded on first use to ~/.cache/huggingface/):
      facebook/musicgen-small   — fast, ~300 MB, good for testing
      facebook/musicgen-medium  — balanced, ~1.5 GB
      facebook/musicgen-large   — best quality, ~3.3 GB
      facebook/musicgen-stereo-large — stereo, best for music production
    """
    name = "local_musicgen"
    _DEFAULT_MODEL = "facebook/musicgen-stereo-large"
    _DURATION = 30  # seconds per generation (increase for longer tracks)

    def __init__(self, model: str = _DEFAULT_MODEL, duration: int = _DEFAULT_DURATION):
        self.model_name = model
        self.duration = duration
        self._model = None  # lazy-load on first generate()

    def _load_model(self):
        if self._model is not None:
            return
        from audiocraft.models import MusicGen
        print(f"  Loading {self.model_name} (first run downloads ~3 GB)...")
        self._model = MusicGen.get_pretrained(self.model_name)
        self._model.set_generation_params(duration=self.duration)
        print(f"  Model loaded.")

    def _build_prompt(self, idea: SongIdea) -> str:
        instrs = ", ".join(idea.instruments[:6]) if idea.instruments else "orchestra"
        parts = [
            idea.genre,
            idea.mood,
            idea.tempo,
            instrs,
        ]
        notes = idea.production_notes[:200] if idea.production_notes else ""
        if notes:
            parts.append(notes)
        return ", ".join(p for p in parts if p)

    def generate(self, idea: SongIdea, output_path: Path) -> Path:
        import torch
        import torchaudio

        output_path.parent.mkdir(parents=True, exist_ok=True)
        self._load_model()

        prompt = self._build_prompt(idea)
        print(f"  Prompt: {prompt[:120]}...")

        wav = self._model.generate([prompt])  # shape: [1, channels, samples]
        wav = wav[0].cpu()

        sample_rate = self._model.sample_rate
        wav_path = output_path.with_suffix(".wav")
        torchaudio.save(str(wav_path), wav, sample_rate)

        mp3_path = _wav_to_mp3(wav_path, output_path)

        # Save metadata
        mp3_path.with_suffix(".json").write_text(json.dumps({
            "title": idea.title, "genre": idea.genre, "mood": idea.mood,
            "tempo": idea.tempo, "key": idea.key, "instruments": idea.instruments,
            "prompt": prompt, "duration_s": self.duration,
            "model": self.model_name, "backend": self.name,
        }, indent=2))
        print(f"  Saved: {mp3_path}")
        return mp3_path

    def is_available(self) -> bool:
        try:
            import audiocraft  # noqa: F401
            return True
        except ImportError:
            return False


# ---------------------------------------------------------------------------
# RunPod MusicGen backend (legacy — use local_musicgen instead)
# ---------------------------------------------------------------------------

class RunPodMusicGenBackend:
    """
    Calls MusicGen on a RunPod serverless endpoint.
    Only needed if not running on EdgeExpert directly.
    Requires: MUSICGEN_ENDPOINT and RUNPOD_API_KEY env vars.
    """
    name = "runpod_musicgen"
    _DURATION = 30

    def _build_prompt(self, idea: SongIdea) -> str:
        instrs = ", ".join(idea.instruments[:5]) if idea.instruments else "orchestra"
        return f"{idea.genre}, {idea.mood}, {idea.tempo}, {instrs}, {idea.production_notes[:150]}"

    def generate(self, idea: SongIdea, output_path: Path) -> Path:
        import httpx, os, base64

        endpoint = os.environ.get("MUSICGEN_ENDPOINT")
        api_key = os.environ.get("RUNPOD_API_KEY")
        if not endpoint or not api_key:
            raise RuntimeError("Set MUSICGEN_ENDPOINT and RUNPOD_API_KEY env vars")

        prompt = self._build_prompt(idea)
        resp = httpx.post(
            endpoint,
            headers={"Authorization": f"Bearer {api_key}"},
            json={"input": {"prompt": prompt, "duration": self._DURATION,
                            "model": "facebook/musicgen-large"}},
            timeout=300,
        )
        resp.raise_for_status()
        result = resp.json()
        output = result.get("output", {})

        output_path.parent.mkdir(parents=True, exist_ok=True)
        if "audio_base64" in output:
            wav_path = output_path.with_suffix(".wav")
            wav_path.write_bytes(base64.b64decode(output["audio_base64"]))
            _wav_to_mp3(wav_path, output_path)
        elif "audio_url" in output:
            output_path.write_bytes(httpx.get(output["audio_url"], timeout=60).content)
        else:
            raise RuntimeError(f"Unexpected RunPod response: {list(output.keys())}")

        output_path.with_suffix(".json").write_text(json.dumps({
            "title": idea.title, "genre": idea.genre, "prompt": prompt,
            "duration_s": self._DURATION, "backend": self.name,
        }, indent=2))
        return output_path

    def is_available(self) -> bool:
        import os
        return bool(os.environ.get("MUSICGEN_ENDPOINT") and os.environ.get("RUNPOD_API_KEY"))


# ---------------------------------------------------------------------------
# Suno API backend
# ---------------------------------------------------------------------------

class SunoBackend:
    """
    Suno official API — generates full songs with vocals.
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
        "runpod": RunPodMusicGenBackend(),
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
        print(f"  [dry-run] [{active.name}] Would generate: {idea.title} → {out}")
        return PipelineResult(idea=idea, output_path=out, success=True)
    if not active.is_available():
        msg = f"Backend '{active.name}' not available. Run: venv/bin/pip install audiocraft"
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
    parser = argparse.ArgumentParser(description="Music production pipeline")
    parser.add_argument("--idea", required=True,
                        help="Path to a songs JSON file from music/ideas.py")
    parser.add_argument("--index", type=int, default=0,
                        help="Which song to produce (0-indexed)")
    parser.add_argument("--all", action="store_true", help="Produce all songs")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would happen without generating")
    parser.add_argument("--backend",
                        choices=["auto", "local_musicgen", "runpod", "suno", "placeholder"],
                        default="auto", help="Audio backend (default: auto)")
    parser.add_argument("--duration", type=int, default=30,
                        help="Audio duration in seconds (default: 30)")
    parser.add_argument("--model",
                        default="facebook/musicgen-stereo-large",
                        help="MusicGen model to use")
    args = parser.parse_args()

    data = json.loads(Path(args.idea).read_text())
    if isinstance(data, dict) and "tracks" in data:
        songs_raw = data["tracks"]
    elif isinstance(data, list):
        songs_raw = data
    else:
        print("Unrecognized JSON format.")
        sys.exit(1)

    songs = [SongIdea(**s) for s in songs_raw]

    if args.backend in ("auto", "local_musicgen"):
        active_backend = LocalMusicGenBackend(model=args.model, duration=args.duration)
    else:
        active_backend = get_backend(args.backend)

    indices = list(range(len(songs))) if args.all else [args.index]
    print(f"Backend: {active_backend.name} | Songs: {len(indices)}")
    for i in indices:
        song = songs[i]
        print(f"\n[{i+1}/{len(indices)}] {song.title}")
        result = run(song, index=i, dry_run=args.dry_run, backend=active_backend)
        if not result.success:
            print(f"  FAILED: {result.error}")


if __name__ == "__main__":
    main()
