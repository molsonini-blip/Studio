from __future__ import annotations

import json
import re
import httpx

from core.news.models import RawArticle, ProcessedScript
from core.news.formatter import build_script

_OLLAMA_URL = "http://localhost:11434/api/generate"
_MODEL = "studio-anchor"

_SYSTEM_PROMPT = """You are a professional broadcast news editor. Your job is to take raw news articles and rewrite them as clean, factual anchor scripts.

RULES — strictly follow all of these:
1. FACTS ONLY. Remove all political opinion, editorial commentary, value judgments, loaded language, and bias.
2. NO attribution phrases like "critics say", "experts fear", "analysts warn", "officials claim". State the fact directly or omit it.
3. SHORT sentences. Maximum 15 words per sentence. Each sentence must stand alone.
4. PLAIN LANGUAGE. Write at a 7th grade reading level. No jargon.
5. ACTIVE VOICE. "The mayor signed the bill." not "The bill was signed by the mayor."
6. PRESENT or SIMPLE PAST tense only. No speculation about the future.
7. NUMBERS: spell out one through ten, use digits for 11 and above.
8. NO filler phrases: "It is worth noting", "Interestingly", "In a surprising turn".
9. OUTPUT FORMAT: Return only a JSON object with two fields:
   - "headline": one sentence, under 12 words, broadcast-style
   - "script": the full rewritten anchor script, plain text, no markdown

Do not include any explanation outside the JSON."""

_USER_TEMPLATE = """Rewrite this news article as a factual anchor script.

TITLE: {title}

ARTICLE:
{body}

Return ONLY valid JSON with "headline" and "script" fields."""


def _call_ollama(prompt: str, system: str = _SYSTEM_PROMPT, timeout: int = 120) -> str:
    payload = {
        "model": _MODEL,
        "prompt": prompt,
        "system": system,
        "stream": False,
        "options": {"temperature": 0.1, "top_p": 0.9, "num_predict": 1024},
    }
    resp = httpx.post(_OLLAMA_URL, json=payload, timeout=timeout)
    resp.raise_for_status()
    return resp.json().get("response", "").strip()


def _extract_json(text: str) -> dict:
    """Extract JSON from LLM response, tolerating minor formatting issues."""
    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Try to find JSON block
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return {}


def process_article(article: RawArticle) -> ProcessedScript:
    """Run the article through the LLM bias filter and return a broadcast-ready script."""
    body = article.full_text or article.summary or article.title
    # Trim to ~2000 chars to stay within context window comfortably
    if len(body) > 2000:
        body = body[:2000] + "..."

    prompt = _USER_TEMPLATE.format(title=article.title, body=body)
    raw_response = _call_ollama(prompt)
    parsed = _extract_json(raw_response)

    headline = parsed.get("headline", article.title).strip()
    script = parsed.get("script", body).strip()

    # Fallback: if LLM returned nothing useful
    if not script or len(script) < 20:
        script = article.summary or article.title

    return build_script(
        headline=headline,
        anchor_text=script,
        source_url=article.url,
        source_name=article.source,
        original_title=article.title,
    )
