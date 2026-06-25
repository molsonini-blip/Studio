#!/usr/bin/env python3
"""
Music production pipeline.

Active backend: MusicGen (Meta AudioCraft) — runs on RunPod GPU.
Fallback: Suno API (cloud, per-generation cost).

Workflow:
  1. ideas.py generates a SongIdea (or load one from JSON)
  2. Pipeline builds a text prompt from the idea
  3. MusicGen on RunPod generates the audio (30-60 seconds per idea)
  4. Output: MP3 + metadata saved to music/genres/<genre>/

RunPod setup: ensure musicgen_endpoint is set in config/settings.yaml
(or set MUSICGEN_ENDPOINT env var pointing to your RunPod serverless endpoint).

Usage:
  python -m music.pipeline --idea music/projects/my_film/songs_20260624.json --index 0
  python -m music.pipeline --idea music/projects/my_film/songs_20260624.json --all
  python -m music.pipeline --dry-run --idea music/projects/my_film/songs_20260624.json
  python -m music.pipeline --backend suno --idea ...   # use Suno API instead
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

# ---------------------------------------------------------------------------
# Audio backend protocol — implement this to wire in a real generator
# ---------------------------------------------------------------------------

class AudioBackend(Protocol):
    """Any audio generation tool must implement this interface."""
    name: str

    def generate(self, idea: SongIdea, output_path: Path) -> Path:
        """Generate audio for idea, save to output_path, return final path."""
        ...

    def is_available(self) -> bool:
        """Return True if the backend can be reached/used right now."""
        ...


# ---------------------------------------------------------------------------
# Placeholder backend — prints what it would do
# ---------------------------------------------------------------------------

class PlaceholderBackend:
    name = "placeholder"

    def generate(self, idea: SongIdea, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        meta = output_path.with_suffix(".json")
        meta.write_text(json.dumps({
            "title": idea.title,
            "genre": idea.genre,
            "mood": idea.mood,
            "tempo": idea.tempo,
            "key": idea.key,
            "instruments": idea.instruments,
            "production_notes": idea.production_notes,
            "status": "pending_audio_backend",
            "note": "Wire in Suno, Udio, or MusicGen to generate actual audio.",
        }, indent=2))
        print(f"  [placeholder] Would generate: {idea.title}")
        print(f"    Genre:    {idea.genre}")
        print(f"    Mood:     {idea.mood} | Tempo: {idea.tempo} | Key: {idea.key}")
        print(f"    Instrs:   {', '.join(idea.instruments)}")
        print(f"    Notes:    {idea.production_notes}")
        print(f"    → Metadata saved: {meta}")
        return output_path

    def is_available(self) -> bool:
        return True


# ---------------------------------------------------------------------------
# MusicGen backend — Meta AudioCraft on RunPod (PRIMARY)
# ---------------------------------------------------------------------------

class MusicGenBackend:
    """
    Calls a MusicGen serverless endpoint on RunPod.

    RunPod setup:
      1. Deploy the audiocraft serverless template on RunPod
         (template ID: audiocraft-musicgen or build from Dockerfile below)
      2. Set MUSICGEN_ENDPOINT env var to your RunPod endpoint URL
         e.g. https://api.runpod.ai/v2/<endpoint_id>/runsync
      3. Set RUNPOD_API_KEY env var

    Dockerfile for RunPod (save as runpod/Dockerfile.musicgen):
      FROM pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime
      RUN pip install audiocraft scipy soundfile
      COPY runpod/musicgen_handler.py /handler.py
      CMD ["python", "-u", "/handler.py"]
    """
    name = "musicgen"
    _DURATION = 30  # seconds of audio per generation

    def _build_prompt(self, idea: SongIdea) -> str:
        instrs = ", ".join(idea.instruments[:5]) if idea.instruments else "orchestra"
        return (
            f"{idea.genre} music, {idea.mood} mood, {idea.tempo}, "
            f"{instrs}, {idea.production_notes[:150]}"
        )

    def generate(self, idea: SongIdea, output_path: Path) -> Path:
        import httpx
        import os
        import base64

        endpoint = os.environ.get("MUSICGEN_ENDPOINT")
        api_key = os.environ.get("RUNPOD_API_KEY")
        if not endpoint or not api_key:
            raise RuntimeError("Set MUSICGEN_ENDPOINT and RUNPOD_API_KEY env vars")

        from shared import budget
        est = budget.estimate_runpod("a10g", self._DURATION / 3600)
        budget.charge("runpod", est, f"musicgen: {idea.title}")

        prompt = self._build_prompt(idea)
        print(f"    MusicGen prompt: {prompt[:100]}...")

        resp = httpx.post(
            endpoint,
            headers={"Authorization": f"Bearer {api_key}"},
            json={"input": {"prompt": prompt, "duration": self._DURATION,
                            "model": "facebook/musicgen-large"}},
            timeout=300,
        )
        resp.raise_for_status()
        result = resp.json()

        # RunPod returns base64-encoded WAV or a URL
        output = result.get("output", {})
        if "audio_base64" in output:
            import io, wave
            audio_bytes = base64.b64decode(output["audio_base64"])
            # Convert WAV bytes to MP3 via ffmpeg if available
            wav_path = output_path.with_suffix(".wav")
            wav_path.write_bytes(audio_bytes)
            _wav_to_mp3(wav_path, output_path)
        elif "audio_url" in output:
            audio = httpx.get(output["audio_url"], timeout=60).content
            output_path.write_bytes(audio)
        else:
            raise RuntimeError(f"Unexpected RunPod response: {list(output.keys())}")

        # Save metadata
        output_path.with_suffix(".json").write_text(json.dumps({
            "title": idea.title, "genre": idea.genre, "mood": idea.mood,
            "tempo": idea.tempo, "key": idea.key,
            "instruments": idea.instruments,
            "prompt": prompt, "duration_s": self._DURATION,
            "backend": self.name,
        }, indent=2))
        return output_path

    def is_available(self) -> bool:
        import os
        return bool(os.environ.get("MUSICGEN_ENDPOINT") and os.environ.get("RUNPOD_API_KEY"))


def _wav_to_mp3(wav_path: Path, mp3_path: Path) -> None:
    """Convert WAV to MP3 using ffmpeg. Falls back to keeping WAV."""
    import subprocess
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(wav_path), "-codec:a", "libmp3lame",
             "-qscale:a", "2", str(mp3_path)],
            capture_output=True, check=True
        )
        wav_path.unlink(missing_ok=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        # ffmpeg not available — keep the WAV
        wav_path.rename(mp3_path.with_suffix(".wav"))


# ---------------------------------------------------------------------------
# Suno API backend (cloud, per-track cost ~$0.05-0.10/track)
# ---------------------------------------------------------------------------

class SunoBackend:
    """
    Suno official API. Set SUNO_API_KEY env var.
    Generates full songs with vocals — better for pop/rock than instrumental.
    Cost: check current Suno pricing at suno.com/api
    """
    name = "suno"

    def generate(self, idea: SongIdea, output_path: Path) -> Path:
        import httpx, os
        api_key = os.environ.get("SUNO_API_KEY")
        if not api_key:
            raise RuntimeError("Set SUNO_API_KEY env var")

        from shared import budget
        budget.charge("suno", 0.10, f"suno: {idea.title}")  # estimate

        prompt = f"{idea.genre}, {idea.mood}, {idea.production_notes[:200]}"
        # Suno API — endpoint may change, check docs.suno.com
        resp = httpx.post(
            "https://api.suno.ai/v1/generate",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"prompt": prompt, "make_instrumental": True},
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()
        # Poll for completion if async
        audio_url = data.get("audio_url") or data.get("clips", [{}])[0].get("audio_url")
        if audio_url:
            audio = httpx.get(audio_url, timeout=60).content
            output_path.write_bytes(audio)
        return output_path

    def is_available(self) -> bool:
        import os
        return bool(os.environ.get("SUNO_API_KEY"))


# ---------------------------------------------------------------------------
# Backend selection — MusicGen is default (free, runs on RunPod)
# ---------------------------------------------------------------------------

def get_backend(name: str = "musicgen") -> AudioBackend:
    backends = {
        "musicgen": MusicGenBackend(),
        "suno": SunoBackend(),
        "placeholder": PlaceholderBackend(),
    }
    return backends.get(name, PlaceholderBackend())


BACKEND: AudioBackend = get_backend(
    "musicgen" if MusicGenBackend().is_available() else "placeholder"
)


# ---------------------------------------------------------------------------
# Pipeline logic
# ---------------------------------------------------------------------------

@dataclass
class PipelineResult:
    idea: SongIdea
    output_path: Path
    success: bool
    error: str = ""


def _output_path_for(idea: SongIdea, index: int) -> Path:
    genre_dir = Path(__file__).parent / "genres" / idea.genre.replace(" ", "_").replace("/", "_")
    genre_dir.mkdir(parents=True, exist_ok=True)
    safe_title = "".join(c if c.isalnum() or c in " _-" else "" for c in idea.title)
    safe_title = safe_title.strip().replace(" ", "_")[:40]
    return genre_dir / f"{index:03d}_{safe_title}.mp3"


def run(idea: SongIdea, index: int = 0, dry_run: bool = False,
        backend: AudioBackend | None = None) -> PipelineResult:
    active = backend or BACKEND
    out = _output_path_for(idea, index)
    if dry_run:
        print(f"  [dry-run] [{active.name}] Would generate: {idea.title} → {out}")
        return PipelineResult(idea=idea, output_path=out, success=True)
    if not active.is_available():
        msg = f"Backend '{active.name}' is not available."
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
                        help="Which song to produce (0-indexed, default: 0)")
    parser.add_argument("--all", action="store_true",
                        help="Produce all songs in the ideas file")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would happen without generating anything")
    parser.add_argument("--backend", choices=["musicgen", "suno", "placeholder"],
                        default=None, help="Override audio backend")
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
    active_backend = get_backend(args.backend) if args.backend else BACKEND

    indices = list(range(len(songs))) if args.all else [args.index]
    print(f"Backend: {active_backend.name} | Songs to process: {len(indices)}")
    for i in indices:
        song = songs[i]
        print(f"\nProcessing [{i+1}/{len(indices)}]: {song.title}")
        result = run(song, index=i, dry_run=args.dry_run, backend=active_backend)
        if not result.success:
            print(f"  FAILED: {result.error}")


if __name__ == "__main__":
    main()
