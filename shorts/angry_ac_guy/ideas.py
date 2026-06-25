#!/usr/bin/env python3
"""
AngryACGuy — episode idea generator.

The character: an HVAC technician who rants about bad installs,
homeowners who DIY, manufacturers cutting corners, and the decline
of the trades. Think "This Old House" meets "angry YouTube mechanic."

Usage:
  python -m shorts.angry_ac_guy.ideas --count 5
  python -m shorts.angry_ac_guy.ideas --topic "refrigerant regulations"
  python -m shorts.angry_ac_guy.ideas --save batch_01
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from shared import ollama

@dataclass
class EpisodeIdea:
    episode_number: int
    title: str          # YouTube-style: "Why Your AC DIES Every Summer (It's Not What You Think)"
    hook: str           # first 5 seconds — what makes viewers keep watching
    topic: str          # the HVAC concept being covered
    rant_angle: str     # what AngryACGuy is angry about specifically
    educational_core: str  # what the viewer actually learns
    visual_gags: list[str] # on-screen moments that punch up the rant
    cta: str            # call to action at the end
    duration_estimate: str  # e.g. "8-12 min", "3-5 min short"
    tags: list[str]     # YouTube tags

_SYSTEM = """You are a YouTube content strategist who writes scripts for AngryACGuy —
a no-nonsense HVAC technician who rants about the HVAC industry's worst practices
while teaching viewers how to protect themselves.

CHARACTER VOICE:
- Direct, opinionated, and a little hot-headed (pun intended)
- Genuine expertise — he knows his stuff cold (also intended)
- Populist — always on the homeowner's side against shady contractors
- Practical — every rant ends with actionable advice
- Catch phrase: "And THAT'S why your AC dies in August!"

CONTENT RULES:
1. Each episode must have a strong enemy: a bad practice, lazy manufacturer, shady contractor, or clueless DIYer
2. The hook must create FOMO — what will the viewer lose if they stop watching?
3. Educational core must be real HVAC knowledge, not fluff
4. Visual gags should be specific (e.g., "cut to: a duct taped with actual duct tape")
5. Return ONLY a JSON array. No preamble.

Schema:
{
  "episode_number": 1,
  "title": "YouTube-style title in ALL CAPS for key words",
  "hook": "first 5-second hook",
  "topic": "HVAC topic",
  "rant_angle": "what AngryACGuy is furious about",
  "educational_core": "what viewers learn",
  "visual_gags": ["list of specific visual moments"],
  "cta": "end of video call to action",
  "duration_estimate": "X-Y min",
  "tags": ["youtube", "tags"]
}"""


def generate_episodes(
    count: int = 5,
    topic: str = "",
    model: str = ollama._DEFAULT_MODEL,
) -> list[EpisodeIdea]:
    ctx = f"\nFocus topic: {topic}" if topic else ""
    prompt = (
        f"Generate {count} AngryACGuy episode ideas.{ctx}\n"
        f"Make each episode distinct — different rants, different educational angles.\n"
        f"Mix short-form (3-5 min) and long-form (8-15 min) content."
    )
    raw = ollama.call_json(prompt, system=_SYSTEM, model=model,
                           temperature=0.9, max_tokens=4000)
    items = raw if isinstance(raw, list) else raw.get("episodes", [])
    return [EpisodeIdea(
        episode_number=e.get("episode_number", i + 1),
        title=e.get("title", f"Episode {i+1}"),
        hook=e.get("hook", ""),
        topic=e.get("topic", ""),
        rant_angle=e.get("rant_angle", ""),
        educational_core=e.get("educational_core", ""),
        visual_gags=e.get("visual_gags", []),
        cta=e.get("cta", ""),
        duration_estimate=e.get("duration_estimate", ""),
        tags=e.get("tags", []),
    ) for i, e in enumerate(items)]


def save_episodes(episodes: list[EpisodeIdea], name: str) -> Path:
    out_dir = Path(__file__).parent / "episodes"
    out_dir.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = out_dir / f"{name}_{ts}.json"
    out.write_text(json.dumps([asdict(e) for e in episodes], indent=2))
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate AngryACGuy episode ideas")
    parser.add_argument("--count", type=int, default=5)
    parser.add_argument("--topic", default="", help="Specific HVAC topic to focus on")
    parser.add_argument("--save", metavar="BATCH_NAME")
    parser.add_argument("--model", default=ollama._DEFAULT_MODEL)
    args = parser.parse_args()

    print(f"Generating {args.count} episode ideas ...")
    episodes = generate_episodes(args.count, args.topic, args.model)
    for ep in episodes:
        print(f"\n[Ep {ep.episode_number}] {ep.title}")
        print(f"  Hook:    {ep.hook}")
        print(f"  Rant:    {ep.rant_angle}")
        print(f"  Learns:  {ep.educational_core}")
        print(f"  Length:  {ep.duration_estimate}")
        if ep.visual_gags:
            print(f"  Visuals: {ep.visual_gags[0]}")

    if args.save:
        path = save_episodes(episodes, args.save)
        print(f"\nSaved to {path}")


if __name__ == "__main__":
    main()
