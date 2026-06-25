"""
Tony Scott documentary — Ollama narration refinement.

Takes each scene's VO text through Ollama and returns
polished, documentary-grade narration in the Ken Burns style.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from shared import ollama
from movie.tony_scott.scenes import Scene

_SYSTEM = """You are a documentary film writer. You are writing the narration for a feature-length
documentary about Tony Scott, the British film director (1944-2012).

TONE: Precise, earned, spare. Think Ken Burns. Think "The Last Dance" but less hagiographic.
Think Errol Morris — willing to sit with ambiguity rather than resolve it falsely.

RULES:
1. Never oversimplify. The man was complicated. Let him be.
2. Short declarative sentences. Vary length for rhythm.
3. Do not sentimentalize the death. Do not explain it.
4. Trust the facts. They are extraordinary. They don't need help.
5. Active voice. Past tense for events. Present tense for legacy.
6. No clichés: "changed cinema", "visionary", "ahead of his time" — none of these.
7. Return ONLY the refined narration text. Nothing else."""

_FIRST_VO_SYSTEM = """You are writing original VO narration for a scene in a documentary about Tony Scott.
Write the spoken narration that a narrator would deliver — not what's on screen, but what we HEAR.
Return only the narration text. 2-4 short paragraphs. Spare, documentary voice."""


def refine(scene: Scene, raw_vo: str) -> str:
    """Refine raw VO text for a scene."""
    prompt = (
        f"Scene {scene.number}: {scene.title}\n"
        f"Emotional beat: {scene.emotional_beat}\n\n"
        f"Original narration:\n{raw_vo}\n\n"
        f"Refine for documentary narration."
    )
    return ollama.call(prompt, system=_SYSTEM, temperature=0.3, max_tokens=512)


def generate_vo(scene: Scene) -> str:
    """Generate original VO text for a scene that has none."""
    prompt = (
        f"Scene: {scene.title}\n"
        f"Act: {scene.act}\n"
        f"What happens: {scene.logline}\n"
        f"Emotional beat: {scene.emotional_beat}\n"
        f"Key interview targets: {', '.join(scene.interview_targets[:3])}\n\n"
        f"Write the narrator's voice-over for this scene."
    )
    return ollama.call(prompt, system=_FIRST_VO_SYSTEM, temperature=0.5, max_tokens=600)


def process_all_scenes(
    save_path: Path | None = None,
    model: str = ollama._DEFAULT_MODEL,
) -> list[dict]:
    """Generate + refine VO for all scenes. Returns list of scene dicts with vo_text."""
    from movie.tony_scott.scenes import SCENES
    results = []
    for scene in SCENES:
        print(f"  Scene {scene.number}: {scene.title} ...")
        raw = generate_vo(scene)
        refined = refine(scene, raw)
        d = {
            "number": scene.number,
            "title": scene.title,
            "act": scene.act,
            "raw_vo": raw,
            "refined_vo": refined,
        }
        results.append(d)
        print(f"    Done. ({len(refined.split())} words)")

    if save_path:
        save_path.write_text(json.dumps(results, indent=2))
        print(f"  Saved to {save_path}")

    return results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--scene", type=int, default=0,
                        help="Process a single scene (0 = all)")
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args()

    if args.scene:
        from movie.tony_scott.scenes import get_scene
        s = get_scene(args.scene)
        if s:
            print(f"Generating VO for Scene {s.number}: {s.title}")
            vo = generate_vo(s)
            print("\nRaw:\n" + vo)
            refined = refine(s, vo)
            print("\nRefined:\n" + refined)
    else:
        out = Path(__file__).parent / "vo_scripts.json" if args.save else None
        process_all_scenes(save_path=out)
