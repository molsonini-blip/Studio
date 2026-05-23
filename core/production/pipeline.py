"""
Full broadcast pipeline orchestrator.

Steps:
  1. Fetch top headlines via RSS/NewsAPI
  2. Filter headlines through Ollama bias-check
  3. Pick anchor roster for this episode (round-robin or random)
  4. Generate TTS audio via ElevenLabs for each anchor
  5. Submit render jobs to RunPod Serverless endpoint (SadTalker)
  6. Collect rendered MP4 segments
  7. Assemble final broadcast (lower-thirds, concat)
  8. Upload to YouTube (stub)
"""
from __future__ import annotations

import datetime
import json
import os
import random
from pathlib import Path

from core.production.serverless_manager import ServerlessManager
from core.production.assembler import assemble_broadcast
from core.production.youtube import upload_to_youtube

STUDIO_DIR = Path(__file__).resolve().parents[2]
ROSTER_JSON = STUDIO_DIR / "data" / "anchors" / "roster.json"
PORTRAITS_DIR = STUDIO_DIR / "data" / "anchors" / "portraits"
TMP_DIR = STUDIO_DIR / "tmp"
OUTPUTS_DIR = STUDIO_DIR / "outputs"


# ── Step 1: Fetch headlines ────────────────────────────────────────────────────

def fetch_headlines(max_items: int = 6) -> list[dict]:
    """Returns list of {title, source, url}. Falls back to RSS on API failure."""
    headlines = _fetch_rss(max_items)
    return headlines[:max_items]


def _fetch_rss(max_items: int) -> list[dict]:
    import xml.etree.ElementTree as ET
    import urllib.request

    feeds = [
        "https://feeds.bbci.co.uk/news/rss.xml",
        "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
        "https://feeds.reuters.com/reuters/topNews",
    ]
    headlines = []
    for url in feeds:
        try:
            with urllib.request.urlopen(url, timeout=10) as resp:
                root = ET.fromstring(resp.read())
            for item in root.iter("item"):
                title = (item.findtext("title") or "").strip()
                link = (item.findtext("link") or "").strip()
                if title:
                    headlines.append({"title": title, "source": url, "url": link})
            if len(headlines) >= max_items * 2:
                break
        except Exception as e:
            print(f"[pipeline] RSS fetch failed ({url}): {e}")
    return headlines


# ── Step 2: Ollama filter ─────────────────────────────────────────────────────

OLLAMA_HOSTS = [
    "http://localhost:11434",
    "http://162.251.146.56:11434",  # StatsDBServer01
]


def filter_headlines(headlines: list[dict], max_items: int = 6) -> list[dict]:
    """Ask Ollama to pick the most newsworthy, least sensational headlines."""
    import requests

    prompt = (
        "You are a neutral news editor. From the following headlines, "
        f"select the {max_items} most factual and newsworthy stories. "
        "Return only a JSON array of the selected headline titles, nothing else.\n\n"
        + "\n".join(f"- {h['title']}" for h in headlines)
    )

    for host in OLLAMA_HOSTS:
        try:
            resp = requests.post(
                f"{host}/api/generate",
                json={"model": "llama3.2:3b", "prompt": prompt, "stream": False},
                timeout=60,
            )
            resp.raise_for_status()
            body = resp.json()
            raw = body.get("response") or body.get("message", {}).get("content", "")
            if not raw:
                continue
            # extract JSON array even if Ollama wraps it in prose
            start, end = raw.find("["), raw.rfind("]")
            if start == -1 or end == -1:
                continue
            selected_titles = json.loads(raw[start:end+1])
            selected = [h for h in headlines if h["title"] in selected_titles]
            if selected:
                print(f"[pipeline] Ollama filter via {host}: {len(selected)} selected")
                return selected[:max_items]
        except Exception as e:
            print(f"[pipeline] Ollama at {host} skipped: {e}")

    print("[pipeline] Ollama unavailable — using top headlines as-is")
    return headlines[:max_items]


# ── Step 3: Pick anchors ──────────────────────────────────────────────────────

def pick_anchors(n: int) -> list[dict]:
    roster = json.loads(ROSTER_JSON.read_text())
    anchors = roster.get("anchors", roster) if isinstance(roster, dict) else roster
    return random.sample(anchors, min(n, len(anchors)))


# ── Step 4: TTS via ElevenLabs ────────────────────────────────────────────────

def generate_tts(anchor: dict, script: str, out_dir: Path) -> Path:
    import requests

    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        raise RuntimeError("ELEVENLABS_API_KEY not set")

    voice_id = anchor.get("elevenlabs_voice_id") or anchor["voice_id"]
    anchor_id = anchor["id"]
    out_path = out_dir / f"{anchor_id}.mp3"

    resp = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
        headers={"xi-api-key": api_key, "Content-Type": "application/json"},
        json={
            "text": script,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
        },
        timeout=60,
    )
    resp.raise_for_status()
    out_path.write_bytes(resp.content)
    return out_path


def build_script(anchor: dict, headline: dict) -> str:
    name = anchor["name"].split()[0]  # first name
    return (
        f"Good evening, I'm {name}. "
        f"{headline['title']}. "
        "We'll have more details as this story develops. Stay with us."
    )


# ── Main pipeline ─────────────────────────────────────────────────────────────

def run(
    anchors_per_episode: int = 3,
    runpod_api_key: str | None = None,
    endpoint_id: str | None = None,
    dry_run: bool = False,
) -> Path | None:
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    episode_dir = OUTPUTS_DIR / f"episode_{timestamp}"
    episode_dir.mkdir(parents=True, exist_ok=True)

    # ── 1. Headlines
    print("[pipeline] Fetching headlines...")
    raw = fetch_headlines(max_items=anchors_per_episode * 3)
    headlines = filter_headlines(raw, max_items=anchors_per_episode)
    print(f"[pipeline] {len(headlines)} headlines selected")

    # ── 2. Anchors
    anchors = pick_anchors(len(headlines))
    segments_meta = [
        {"anchor": a, "headline": h, "script": build_script(a, h)}
        for a, h in zip(anchors, headlines)
    ]

    # ── 3. TTS
    print("[pipeline] Generating TTS audio...")
    for seg in segments_meta:
        if dry_run:
            print(f"  [dry] TTS for {seg['anchor']['id']}: {seg['script'][:60]}...")
            seg["audio"] = TMP_DIR / f"{seg['anchor']['id']}.mp3"
        else:
            seg["audio"] = generate_tts(seg["anchor"], seg["script"], TMP_DIR)
            print(f"  {seg['anchor']['id']} -> {seg['audio'].name}")

    if dry_run:
        print("[pipeline] Dry run complete — skipping GPU render and assembly.")
        return None

    # ── 4-6. RunPod Serverless render (auto-scales, $0 when idle)
    sl = ServerlessManager(
        api_key=runpod_api_key or os.environ.get("RUNPOD_API_KEY"),
        endpoint_id=endpoint_id or os.environ.get("RUNPOD_ENDPOINT_ID"),
    )

    print("[pipeline] Submitting render jobs to serverless endpoint...")
    render_jobs = [
        {
            "anchor_id": seg["anchor"]["id"],
            "portrait": PORTRAITS_DIR / f"{seg['anchor']['id']}.png",
            "audio": seg["audio"],
        }
        for seg in segments_meta
    ]
    mp4_paths = sl.render_all(render_jobs, episode_dir)
    for seg, mp4 in zip(segments_meta, mp4_paths):
        seg["local_mp4"] = mp4

    # ── 10. Assemble
    print("[pipeline] Assembling broadcast...")
    final_video = OUTPUTS_DIR / f"broadcast_{timestamp}.mp4"
    assemble_broadcast(
        segments=[
            {
                "mp4": seg["local_mp4"],
                "anchor_name": seg["anchor"]["name"],
                "headline": seg["headline"]["title"],
            }
            for seg in segments_meta
        ],
        output=final_video,
    )
    print(f"[pipeline] Broadcast ready: {final_video}")

    # ── 11. YouTube (stub)
    upload_to_youtube(
        video_path=final_video,
        title=f"AI News Now — {datetime.datetime.now().strftime('%B %d, %Y')}",
        tags=["news", "AI", "breaking news"],
    )

    return final_video
