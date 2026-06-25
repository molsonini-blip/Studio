"""
Shared Ollama client for all Studio pipelines.

All modules that call Ollama should import from here instead of
implementing their own HTTP calls.
"""
from __future__ import annotations

import json
import re
from typing import Any

import httpx

# All pipelines run on EdgeExpert — Ollama is local
_HOSTS = [
    "http://localhost:11434",
]
_DEFAULT_MODEL = "llama3.2:3b"
_DEFAULT_TIMEOUT = 180


def call(
    prompt: str,
    *,
    system: str = "",
    model: str = _DEFAULT_MODEL,
    temperature: float = 0.7,
    top_p: float = 0.9,
    max_tokens: int = 2048,
    timeout: int = _DEFAULT_TIMEOUT,
) -> str:
    """Send a prompt to Ollama and return the response text."""
    payload: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
            "top_p": top_p,
            "num_predict": max_tokens,
        },
    }
    if system:
        payload["system"] = system

    last_err: Exception | None = None
    for host in _HOSTS:
        try:
            resp = httpx.post(f"{host}/api/generate", json=payload, timeout=timeout)
            resp.raise_for_status()
            return resp.json().get("response", "").strip()
        except Exception as e:
            last_err = e
            continue

    raise RuntimeError(f"Ollama unreachable on all hosts. Last error: {last_err}")


def call_json(
    prompt: str,
    *,
    system: str = "",
    model: str = _DEFAULT_MODEL,
    temperature: float = 0.5,
    max_tokens: int = 2048,
    timeout: int = _DEFAULT_TIMEOUT,
) -> dict | list:
    """Call Ollama and parse the response as JSON.

    Strips markdown code fences before parsing.
    """
    raw = call(
        prompt,
        system=system,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
    )
    # Strip ```json ... ``` fences if present
    clean = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
    clean = re.sub(r"\s*```$", "", clean, flags=re.MULTILINE).strip()
    # Try direct parse
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        pass
    # Find first {...} or [...] block
    m = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", clean)
    if m:
        return json.loads(m.group(1))
    raise ValueError(f"No valid JSON in Ollama response:\n{raw[:500]}")


def list_models(timeout: int = 10) -> list[str]:
    """Return available model names from the first reachable Ollama host."""
    for host in _HOSTS:
        try:
            resp = httpx.get(f"{host}/api/tags", timeout=timeout)
            resp.raise_for_status()
            return [m["name"] for m in resp.json().get("models", [])]
        except Exception:
            continue
    return []
