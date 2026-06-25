#!/usr/bin/env python3
"""
Music idea generator — powered by Ollama.

Generates song concepts, soundtrack briefs, and full album ideas
organized by genre. Primary focus: movie soundtracks.

Usage:
  # Generate 5 soundtrack ideas for a war film:
  python -m music.ideas --genre soundtracks --context "World War II drama" --count 5

  # Generate rock song ideas:
  python -m music.ideas --genre rock --count 3

  # Generate a full soundtrack brief (multiple tracks for one film):
  python -m music.ideas --soundtrack --context "gritty 1970s detective thriller"

  # List all genres:
  python -m music.ideas --list-genres

  # Save ideas to a project folder:
  python -m music.ideas --genre soundtracks --context "space opera" --save my_space_opera
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from shared import ollama

# ---------------------------------------------------------------------------
# Genre definitions
# ---------------------------------------------------------------------------

GENRES: dict[str, dict] = {
    "soundtracks": {
        "description": "Orchestral and hybrid scores for film, TV, and games",
        "style_notes": "Leitmotifs, emotional arcs, scene-specific cues, temp track thinking",
        "instruments": "Orchestra, synths, choir, ethnic instruments, solo strings/piano",
        "references": "Hans Zimmer, John Williams, Ennio Morricone, Jonny Greenwood",
    },
    "rock": {
        "description": "Classic rock, hard rock, alternative, and metal",
        "style_notes": "Guitar-driven, verse-chorus-verse, power and attitude",
        "instruments": "Electric guitar, bass, drums, vocals",
        "references": "Zeppelin, AC/DC, Foo Fighters, Black Sabbath",
    },
    "country": {
        "description": "Country, Americana, bluegrass, folk",
        "style_notes": "Storytelling lyrics, twang, authentic emotion",
        "instruments": "Acoustic guitar, pedal steel, fiddle, banjo, upright bass",
        "references": "Johnny Cash, Emmylou Harris, Townes Van Zandt, Sturgill Simpson",
    },
    "hip_hop": {
        "description": "Hip-hop, rap, trap, R&B, and soul",
        "style_notes": "Rhythm-forward, lyrical density, sampling culture",
        "instruments": "808 drums, bass, samples, vocals, piano",
        "references": "Kendrick Lamar, J Dilla, Nas, OutKast",
    },
    "electronic": {
        "description": "Electronic, EDM, ambient, lo-fi, house, techno",
        "style_notes": "Sound design-forward, texture and space, dance or headphone listening",
        "instruments": "Synthesizers, drum machines, samplers, effects processing",
        "references": "Aphex Twin, Daft Punk, Brian Eno, Burial",
    },
    "jazz": {
        "description": "Jazz, big band, fusion, and bebop",
        "style_notes": "Improvisation, swing, complex harmony, call and response",
        "instruments": "Piano, upright bass, drums, horns, guitar",
        "references": "Miles Davis, Coltrane, Bill Evans, Charles Mingus",
    },
    "classical": {
        "description": "Classical, contemporary classical, neoclassical",
        "style_notes": "Formal structure, development and variation, dynamics",
        "instruments": "Piano, strings, woodwinds, brass, full orchestra",
        "references": "Bach, Beethoven, Arvo Pärt, Max Richter",
    },
    "pop": {
        "description": "Contemporary pop, indie pop, synth-pop",
        "style_notes": "Hook-driven, accessible, production-first",
        "instruments": "Vocals, piano/keys, programmed drums, synths, bass",
        "references": "Taylor Swift, Charli XCX, Lorde, The Weeknd",
    },
}

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class SongIdea:
    title: str
    genre: str
    mood: str
    tempo: str          # e.g. "slow and heavy", "120 BPM uptempo"
    key: str            # e.g. "D minor", "E major"
    instruments: list[str]
    scene_or_context: str   # what moment / film scene / emotion this serves
    lyric_hook: str         # one memorable line or hook phrase
    production_notes: str   # how it should sound, production direction
    duration_estimate: str  # e.g. "3:30", "2:00 underscore cue"

@dataclass
class SoundtrackBrief:
    title: str
    film_concept: str
    total_tracks: int
    themes: list[str]      # named leitmotifs / recurring themes
    tracks: list[SongIdea]
    emotional_arc: str     # how music evolves over the film's three acts


# ---------------------------------------------------------------------------
# Ollama prompts
# ---------------------------------------------------------------------------

_SONG_SYSTEM = """You are a professional music composer and songwriter with deep knowledge of all genres.
You generate creative, specific, original song ideas — not generic descriptions.

RULES:
1. Be specific. Name real keys, real BPM ranges, real reference points.
2. Avoid clichés. Give each idea a distinct angle.
3. The lyric_hook must be a single memorable line — the kind you can't shake.
4. production_notes should tell a producer exactly how this should sound.
5. Return ONLY a JSON array of song objects. No preamble, no explanation.

JSON schema for each song:
{
  "title": "song title",
  "genre": "genre name",
  "mood": "emotional feel",
  "tempo": "tempo description",
  "key": "musical key",
  "instruments": ["list", "of", "instruments"],
  "scene_or_context": "what moment or scene this serves",
  "lyric_hook": "one killer line",
  "production_notes": "how this should sound",
  "duration_estimate": "estimated length"
}"""

_SOUNDTRACK_SYSTEM = """You are a Hollywood film composer. You design complete soundtrack briefs for films —
the full emotional and musical arc, with specific cues and themes.

RULES:
1. Think like Hans Zimmer or Ennio Morricone — music that serves the story.
2. Give each theme a NAME and describe when it appears.
3. Each track is a specific cue: its moment in the film, its emotional purpose, its sound.
4. Return ONLY a valid JSON object. No preamble.

JSON schema:
{
  "title": "soundtrack title",
  "film_concept": "film description",
  "total_tracks": number,
  "themes": ["Theme Name: description of when it appears and what it represents"],
  "emotional_arc": "how the music evolves across three acts",
  "tracks": [array of song objects per the song schema]
}"""


def _song_user_prompt(genre: str, context: str, count: int) -> str:
    g = GENRES[genre]
    ctx = f"\nContext/setting: {context}" if context else ""
    return (
        f"Genre: {genre} — {g['description']}\n"
        f"Style: {g['style_notes']}\n"
        f"Typical instruments: {g['instruments']}\n"
        f"Reference artists: {g['references']}"
        f"{ctx}\n\n"
        f"Generate {count} original, distinct song ideas for this genre. "
        f"Make each one feel like a real, fully-realized concept."
    )


def _soundtrack_user_prompt(context: str, track_count: int) -> str:
    return (
        f"Film concept: {context}\n\n"
        f"Design a complete film soundtrack with {track_count} cues. "
        f"Include named leitmotifs that recur and evolve. "
        f"Map the music to the three-act emotional arc of the story."
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_songs(
    genre: str,
    count: int = 5,
    context: str = "",
    model: str = ollama._DEFAULT_MODEL,
) -> list[SongIdea]:
    """Generate song ideas for a given genre."""
    if genre not in GENRES:
        raise ValueError(f"Unknown genre '{genre}'. Available: {list(GENRES)}")

    raw = ollama.call_json(
        _song_user_prompt(genre, context, count),
        system=_SONG_SYSTEM,
        model=model,
        temperature=0.85,
        max_tokens=3000,
    )
    songs = raw if isinstance(raw, list) else raw.get("songs", [])
    return [
        SongIdea(
            title=s.get("title", "Untitled"),
            genre=s.get("genre", genre),
            mood=s.get("mood", ""),
            tempo=s.get("tempo", ""),
            key=s.get("key", ""),
            instruments=s.get("instruments", []),
            scene_or_context=s.get("scene_or_context", ""),
            lyric_hook=s.get("lyric_hook", ""),
            production_notes=s.get("production_notes", ""),
            duration_estimate=s.get("duration_estimate", ""),
        )
        for s in songs
    ]


def generate_soundtrack(
    context: str,
    track_count: int = 12,
    model: str = ollama._DEFAULT_MODEL,
) -> SoundtrackBrief:
    """Generate a full soundtrack brief for a film concept."""
    raw = ollama.call_json(
        _soundtrack_user_prompt(context, track_count),
        system=_SOUNDTRACK_SYSTEM,
        model=model,
        temperature=0.8,
        max_tokens=4000,
    )
    tracks = [
        SongIdea(
            title=t.get("title", "Untitled"),
            genre="soundtracks",
            mood=t.get("mood", ""),
            tempo=t.get("tempo", ""),
            key=t.get("key", ""),
            instruments=t.get("instruments", []),
            scene_or_context=t.get("scene_or_context", ""),
            lyric_hook=t.get("lyric_hook", ""),
            production_notes=t.get("production_notes", ""),
            duration_estimate=t.get("duration_estimate", ""),
        )
        for t in raw.get("tracks", [])
    ]
    return SoundtrackBrief(
        title=raw.get("title", "Untitled Soundtrack"),
        film_concept=raw.get("film_concept", context),
        total_tracks=raw.get("total_tracks", len(tracks)),
        themes=raw.get("themes", []),
        tracks=tracks,
        emotional_arc=raw.get("emotional_arc", ""),
    )


def save_ideas(ideas: list[SongIdea] | SoundtrackBrief, project_name: str) -> Path:
    """Save ideas to music/projects/<project_name>/."""
    root = Path(__file__).parent / "projects" / project_name
    root.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    if isinstance(ideas, SoundtrackBrief):
        out = root / f"soundtrack_{ts}.json"
        out.write_text(json.dumps(asdict(ideas), indent=2))
    else:
        out = root / f"songs_{ts}.json"
        out.write_text(json.dumps([asdict(i) for i in ideas], indent=2))
    return out


def print_song(song: SongIdea, index: int | None = None) -> None:
    prefix = f"[{index}] " if index is not None else ""
    print(f"\n{prefix}{song.title.upper()} ({song.genre})")
    print(f"  Mood:      {song.mood}")
    print(f"  Tempo:     {song.tempo}  |  Key: {song.key}")
    print(f"  Instrs:    {', '.join(song.instruments)}")
    print(f"  Context:   {song.scene_or_context}")
    print(f"  Hook:      \"{song.lyric_hook}\"")
    print(f"  Sound:     {song.production_notes}")
    print(f"  Length:    {song.duration_estimate}")


def print_soundtrack(brief: SoundtrackBrief) -> None:
    print(f"\n{'='*60}")
    print(f"SOUNDTRACK: {brief.title}")
    print(f"Film:       {brief.film_concept}")
    print(f"Tracks:     {brief.total_tracks}")
    print(f"\nEmotional Arc:\n  {brief.emotional_arc}")
    print(f"\nThemes:")
    for t in brief.themes:
        print(f"  • {t}")
    print(f"\nTrack List:")
    for i, track in enumerate(brief.tracks, 1):
        print_song(track, i)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate music ideas via Ollama")
    parser.add_argument("--genre", default="soundtracks", choices=list(GENRES),
                        help="Music genre (default: soundtracks)")
    parser.add_argument("--context", default="",
                        help="Film concept, setting, or theme context")
    parser.add_argument("--count", type=int, default=5,
                        help="Number of song ideas (default: 5)")
    parser.add_argument("--soundtrack", action="store_true",
                        help="Generate a full soundtrack brief instead of individual songs")
    parser.add_argument("--tracks", type=int, default=12,
                        help="Number of tracks for --soundtrack mode (default: 12)")
    parser.add_argument("--save", metavar="PROJECT",
                        help="Save results to music/projects/PROJECT/")
    parser.add_argument("--list-genres", action="store_true",
                        help="List available genres and exit")
    parser.add_argument("--model", default=ollama._DEFAULT_MODEL,
                        help="Ollama model to use")
    args = parser.parse_args()

    if args.list_genres:
        print("Available genres:")
        for name, g in GENRES.items():
            print(f"  {name:15} — {g['description']}")
        return

    if args.soundtrack:
        ctx = args.context or "a cinematic drama with action and emotion"
        print(f"Generating soundtrack brief for: '{ctx}' ...")
        brief = generate_soundtrack(ctx, track_count=args.tracks, model=args.model)
        print_soundtrack(brief)
        if args.save:
            path = save_ideas(brief, args.save)
            print(f"\nSaved to {path}")
    else:
        print(f"Generating {args.count} {args.genre} ideas ...")
        songs = generate_songs(args.genre, count=args.count, context=args.context, model=args.model)
        for i, song in enumerate(songs, 1):
            print_song(song, i)
        if args.save:
            path = save_ideas(songs, args.save)
            print(f"\nSaved to {path}")


if __name__ == "__main__":
    main()
