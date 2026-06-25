"""
Jim Hall movie — Ollama narration refinement.

Sends each scene's raw VO text through the local Ollama LLM and returns
a polished, documentary-grade narration script. Falls back to the original
text if the model is unavailable.
"""
from __future__ import annotations

import json
import re

import requests

from core.movie.scenes import OLLAMA_HOSTS, OLLAMA_MODEL

_SYSTEM_PROMPT = """You are a documentary film writer specializing in American history and motorsport.
Your task is to refine narration scripts for a Hollywood-caliber documentary about Jim Hall
and his Chaparral racing cars.

RULES — follow all of these strictly:
1. STYLE: Spare, precise, earned. Match the tone of Ken Burns documentaries or "The Right Stuff."
   No purple prose. No hype. The facts ARE extraordinary — trust them.
2. RHYTHM: Short, declarative sentences. Vary length for pace — short punches, occasional longer builds.
   Read aloud before finalizing. It must sound right spoken.
3. FACTS: Do not invent facts. Work only with what is provided. You may rearrange and sharpen phrasing.
4. VOICE: Third person. Past tense for events. Present tense for legacy statements.
5. NO CLICHÉS: "Changed the game", "ahead of its time", "legend", "iconic" — avoid all of these.
   The work speaks for itself.
6. LENGTH: Return approximately the same length as the input — no longer. Do not pad.
7. OUTPUT FORMAT: Return ONLY the refined narration text. No preamble, no explanation, no quotes around the text.
"""

_USER_TEMPLATE = """Scene: {title}

Original narration:
{vo_text}

Refine this for a Hollywood documentary narrator. Return only the refined text."""


def _call_ollama(prompt: str, timeout: int = 180) -> str | None:
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "system": _SYSTEM_PROMPT,
        "stream": False,
        "options": {"temperature": 0.3, "top_p": 0.9, "num_predict": 512},
    }
    for host in OLLAMA_HOSTS:
        try:
            resp = requests.post(
                f"{host}/api/generate",
                json=payload,
                timeout=timeout,
            )
            resp.raise_for_status()
            text = resp.json().get("response", "").strip()
            if text and len(text) > 20:
                print(f"  [ollama] refined via {host}")
                return text
        except Exception as e:
            print(f"  [ollama] {host} unavailable: {e}")
    return None


def refine_scene_vo(scene: dict) -> str:
    """
    Returns refined narration text for a scene.
    Falls back to original VO if Ollama is unavailable.
    """
    original = scene["vo"]
    refined = _call_ollama(
        _USER_TEMPLATE.format(title=scene["title"], vo_text=original)
    )
    if refined:
        return refined
    print(f"  [narrator] using original VO for scene {scene['id']}: {scene['slug']}")
    return original


def refine_all_scenes(scenes: list[dict], skip_ollama: bool = False) -> list[dict]:
    """
    Returns list of scenes with an added 'refined_vo' field.
    If skip_ollama=True, refined_vo == original vo (fast mode).
    """
    results = []
    for scene in scenes:
        if skip_ollama:
            scene = {**scene, "refined_vo": scene["vo"]}
        else:
            print(f"  [narrator] refining scene {scene['id']}: {scene['slug']}")
            scene = {**scene, "refined_vo": refine_scene_vo(scene)}
        results.append(scene)
    return results
