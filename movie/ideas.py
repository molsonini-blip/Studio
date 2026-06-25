#!/usr/bin/env python3
"""
Movie idea generator — powered by Ollama.

Generates Hollywood-style movie concepts, loglines, treatments,
and character breakdowns.

Usage:
  python -m movie.ideas --genre drama --count 3
  python -m movie.ideas --treatment --concept "a disgraced NASCAR driver finds redemption"
  python -m movie.ideas --save my_racing_film --concept "..."
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from shared import ollama

GENRES = ["drama", "thriller", "action", "comedy", "sci-fi",
          "horror", "western", "documentary", "biopic", "heist"]

@dataclass
class MovieConcept:
    title: str
    genre: str
    logline: str        # one sentence: protagonist + goal + obstacle
    hook: str           # what makes this different from every other film
    protagonist: str
    antagonist: str
    setting: str
    three_act_summary: str
    comp_titles: list[str]   # "this meets that" comps
    tone: str
    budget_tier: str    # "micro (<$1M)", "indie ($1-10M)", "studio ($50M+)"

@dataclass
class TreatmentBeat:
    act: str
    beat: str
    scene_description: str

@dataclass
class Treatment:
    concept: MovieConcept
    beats: list[TreatmentBeat]
    themes: list[str]
    opening_image: str
    closing_image: str


_CONCEPT_SYSTEM = """You are a Hollywood development executive with taste. You generate
original, commercially viable movie concepts that haven't been made before.

RULES:
1. The logline must follow: [Protagonist] must [goal] before [stakes/deadline], but [obstacle].
2. Comp titles must be real films. Format: "Film A meets Film B."
3. Be specific — name the setting, time period, and visual style.
4. Return ONLY a JSON array of concepts. No preamble.

Schema per concept:
{
  "title": "...",
  "genre": "...",
  "logline": "...",
  "hook": "what makes this original",
  "protagonist": "name + brief description",
  "antagonist": "name or force opposing the protagonist",
  "setting": "specific place and time",
  "three_act_summary": "brief arc across three acts",
  "comp_titles": ["Film A meets Film B"],
  "tone": "...",
  "budget_tier": "micro|indie|studio"
}"""

_TREATMENT_SYSTEM = """You are a screenwriter developing a beat sheet for a film.
Return ONLY valid JSON. No preamble.

Schema:
{
  "themes": ["list of thematic concerns"],
  "opening_image": "the very first image of the film",
  "closing_image": "the final image — bookend to the opening",
  "beats": [
    {
      "act": "Act 1|Act 2a|Midpoint|Act 2b|Act 3",
      "beat": "beat name (e.g. Inciting Incident, Break Into Two)",
      "scene_description": "what happens in this scene, 2-3 sentences"
    }
  ]
}"""


def generate_concepts(
    genre: str = "drama",
    count: int = 3,
    context: str = "",
    model: str = ollama._DEFAULT_MODEL,
) -> list[MovieConcept]:
    ctx = f"\nSpecific direction: {context}" if context else ""
    prompt = f"Genre: {genre}\nGenerate {count} original movie concepts.{ctx}"
    raw = ollama.call_json(prompt, system=_CONCEPT_SYSTEM, model=model,
                           temperature=0.9, max_tokens=4000)
    items = raw if isinstance(raw, list) else raw.get("concepts", [])
    return [MovieConcept(
        title=c.get("title", "Untitled"),
        genre=c.get("genre", genre),
        logline=c.get("logline", ""),
        hook=c.get("hook", ""),
        protagonist=c.get("protagonist", ""),
        antagonist=c.get("antagonist", ""),
        setting=c.get("setting", ""),
        three_act_summary=c.get("three_act_summary", ""),
        comp_titles=c.get("comp_titles", []),
        tone=c.get("tone", ""),
        budget_tier=c.get("budget_tier", "indie"),
    ) for c in items]


def generate_treatment(concept_text: str, model: str = ollama._DEFAULT_MODEL) -> dict:
    prompt = f"Develop a full beat sheet for this film concept:\n\n{concept_text}"
    return ollama.call_json(prompt, system=_TREATMENT_SYSTEM, model=model,
                            temperature=0.8, max_tokens=4000)


def save_concept(concepts: list[MovieConcept], name: str) -> Path:
    out = Path(__file__).parent / "projects" / f"{name}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps([asdict(c) for c in concepts], indent=2))
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate movie concepts via Ollama")
    parser.add_argument("--genre", default="drama", choices=GENRES)
    parser.add_argument("--count", type=int, default=3)
    parser.add_argument("--concept", default="", help="Specific concept direction")
    parser.add_argument("--treatment", action="store_true",
                        help="Generate a full beat-sheet treatment")
    parser.add_argument("--save", metavar="NAME")
    parser.add_argument("--model", default=ollama._DEFAULT_MODEL)
    args = parser.parse_args()

    concepts = generate_concepts(args.genre, args.count, args.concept, args.model)
    for i, c in enumerate(concepts, 1):
        print(f"\n[{i}] {c.title.upper()} ({c.genre} | {c.budget_tier})")
        print(f"  {c.logline}")
        print(f"  Hook:   {c.hook}")
        print(f"  Comps:  {', '.join(c.comp_titles)}")
        print(f"  Tone:   {c.tone}")
        print(f"  Arc:    {c.three_act_summary}")

    if args.treatment and concepts:
        print(f"\n--- TREATMENT: {concepts[0].title} ---")
        t = generate_treatment(asdict(concepts[0]).__str__(), args.model)
        print(json.dumps(t, indent=2))

    if args.save:
        path = save_concept(concepts, args.save)
        print(f"\nSaved to {path}")


if __name__ == "__main__":
    main()
