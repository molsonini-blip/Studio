#!/usr/bin/env python3
"""
Tony Scott Documentary — Continuous Research Daemon.

Runs indefinitely on EdgeExpert server. Every cycle it:
  1. Picks the next search query from a rotating list
  2. Searches the web (DuckDuckGo, free) and news (NewsAPI/GNews)
  3. For each new URL: fetches content, summarizes via Ollama, classifies legally
  4. Adds to the source registry with full legal metadata
  5. Appends findings to a rolling research log
  6. Sleeps, then repeats

Deploy on server:
  pip install duckduckgo-search httpx
  nohup python movie/tony_scott/research_loop.py > /opt/studio/logs/tony_scott_research.log 2>&1 &

Monitor:
  tail -f /opt/studio/logs/tony_scott_research.log

Stop:
  kill $(cat /opt/studio/logs/tony_scott_research.pid)

Requirements:
  pip install duckduckgo-search httpx
"""
from __future__ import annotations

import json
import os
import signal
import sys
import time
from datetime import datetime, date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from shared import ollama
from movie.tony_scott.sources.registry import (
    Registry, Source, SourceType, UseType, CopyrightStatus
)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

LOG_FILE    = Path("/opt/studio/logs/tony_scott_research.log")
PID_FILE    = Path("/opt/studio/logs/tony_scott_research.pid")
NOTES_FILE  = Path(__file__).parent / "sources" / "research_notes.md"

# Search interval: 45 minutes between cycles (stays within DuckDuckGo rate limits)
SLEEP_SECONDS = 45 * 60

# Max results to process per search query
MAX_RESULTS_PER_QUERY = 8

# Search queries — rotated through in order, cycling indefinitely
SEARCH_QUERIES: list[dict] = [
    # Core biography
    {"q": "Tony Scott director biography", "topic": "biography"},
    {"q": "Tony Scott childhood Northumberland art school", "topic": "biography"},
    {"q": "Tony Scott Ridley Scott relationship brothers", "topic": "biography"},
    {"q": "Tony Scott death 2012 Vincent Thomas Bridge", "topic": "death"},
    {"q": "Tony Scott cancer diagnosis 2012", "topic": "death"},
    {"q": "Tony Scott coroner report 2012", "topic": "death"},
    # Filmography
    {"q": "Tony Scott Top Gun production behind scenes 1986", "topic": "films"},
    {"q": "Tony Scott Man on Fire visual style cinematography", "topic": "visual_style"},
    {"q": "Tony Scott True Romance Tarantino", "topic": "films"},
    {"q": "Tony Scott Crimson Tide Denzel Washington", "topic": "films"},
    {"q": "Tony Scott Enemy of the State NSA surveillance", "topic": "films"},
    {"q": "Tony Scott Domino 2005 making of", "topic": "films"},
    {"q": "Tony Scott Unstoppable 2010 final film", "topic": "films"},
    {"q": "Tony Scott Beverly Hills Cop II Days of Thunder", "topic": "films"},
    # Visual style
    {"q": "Tony Scott cinematography techniques bleach bypass", "topic": "visual_style"},
    {"q": "Tony Scott film techniques multiple cameras", "topic": "visual_style"},
    {"q": "Tony Scott Marlboro commercial techniques", "topic": "visual_style"},
    {"q": "Tony Scott Dan Mindel cinematographer", "topic": "visual_style"},
    {"q": "Tony Scott Dariusz Wolski", "topic": "visual_style"},
    {"q": "Tony Scott Chris Lebenzon editor", "topic": "visual_style"},
    # Early career
    {"q": "Tony Scott Loving Memory 1971 student film Cannes", "topic": "early_career"},
    {"q": "Tony Scott One of the Missing 1969 BAFTA", "topic": "early_career"},
    {"q": "Tony Scott RSA Films commercials 1970s", "topic": "early_career"},
    {"q": "Tony Scott Chanel No 5 commercial Catherine Deneuve", "topic": "early_career"},
    {"q": "Tony Scott Royal College of Art London", "topic": "early_career"},
    {"q": "Tony Scott The Hunger 1983 David Bowie", "topic": "films"},
    # Critical reception
    {"q": "Tony Scott critical reassessment auteur", "topic": "criticism"},
    {"q": "vulgar auteurism Tony Scott Michael Mann", "topic": "criticism"},
    {"q": "Tony Scott legacy documentary filmmaker", "topic": "criticism"},
    {"q": "Tony Scott better than Ridley Scott comparison", "topic": "criticism"},
    # Personal
    {"q": "Tony Scott Dolomites climbing alpinist", "topic": "personal"},
    {"q": "Tony Scott family Donna Scott twins", "topic": "personal"},
    {"q": "Tony Scott depression mental health", "topic": "personal"},
    {"q": "Tony Scott interview personal life", "topic": "personal"},
    # Archival/academic
    {"q": "ReFocus Films Tony Scott Edinburgh University Press", "topic": "academic"},
    {"q": "Tony Scott film studies academic analysis", "topic": "academic"},
    {"q": "Tony Scott BFI archive footage", "topic": "archival"},
    {"q": "Tony Scott Navy cooperation Top Gun DOD", "topic": "archival"},
    # New angles
    {"q": "Tony Scott influence on contemporary directors", "topic": "legacy"},
    {"q": "Tony Scott Top Gun Maverick legacy 2022", "topic": "legacy"},
    {"q": "Tony Scott Quentin Tarantino friendship collaboration", "topic": "relationships"},
    {"q": "Tony Scott Don Simpson Jerry Bruckheimer", "topic": "relationships"},
    {"q": "Tony Scott Tom Cruise relationship", "topic": "relationships"},
    {"q": "Tony Scott commercial advertising work UK", "topic": "early_career"},
]

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def log(msg: str) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def append_notes(content: str) -> None:
    NOTES_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(NOTES_FILE, "a", encoding="utf-8") as f:
        f.write(content + "\n")

# ---------------------------------------------------------------------------
# Web search (DuckDuckGo — free, no API key)
# ---------------------------------------------------------------------------

def search_ddg(query: str, max_results: int = MAX_RESULTS_PER_QUERY) -> list[dict]:
    """Search DuckDuckGo. Returns list of {title, url, body}."""
    try:
        from duckduckgo_search import DDGS
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "body": r.get("body", ""),
                })
        return results
    except ImportError:
        log("WARNING: duckduckgo-search not installed. pip install duckduckgo-search")
        return []
    except Exception as e:
        log(f"  DDG search error: {e}")
        return []


def search_newsapi(query: str, max_results: int = 5) -> list[dict]:
    """Search NewsAPI if key available."""
    api_key = os.environ.get("NEWSAPI_KEY")
    if not api_key:
        return []
    try:
        import httpx
        resp = httpx.get(
            "https://newsapi.org/v2/everything",
            params={"q": query, "pageSize": max_results,
                    "sortBy": "relevancy", "language": "en"},
            headers={"X-Api-Key": api_key},
            timeout=15,
        )
        if resp.status_code == 200:
            articles = resp.json().get("articles", [])
            return [{"title": a.get("title", ""), "url": a.get("url", ""),
                     "body": a.get("description", "") + " " + (a.get("content") or "")}
                    for a in articles if a.get("url")]
    except Exception as e:
        log(f"  NewsAPI error: {e}")
    return []

# ---------------------------------------------------------------------------
# Content fetching + Ollama classification
# ---------------------------------------------------------------------------

def fetch_text(url: str, max_chars: int = 8000) -> str:
    """Fetch page text, strip HTML."""
    try:
        import httpx
        from html.parser import HTMLParser

        class TextExtractor(HTMLParser):
            def __init__(self):
                super().__init__()
                self._text: list[str] = []
                self._skip = False
            def handle_starttag(self, tag, attrs):
                if tag in ("script", "style", "nav", "footer", "header"):
                    self._skip = True
            def handle_endtag(self, tag):
                if tag in ("script", "style", "nav", "footer", "header"):
                    self._skip = False
            def handle_data(self, data):
                if not self._skip:
                    stripped = data.strip()
                    if stripped:
                        self._text.append(stripped)
            def get_text(self):
                return " ".join(self._text)

        headers = {"User-Agent": "Mozilla/5.0 (research bot for documentary film)"}
        resp = httpx.get(url, headers=headers, timeout=20, follow_redirects=True)
        parser = TextExtractor()
        parser.feed(resp.text)
        return parser.get_text()[:max_chars]
    except Exception as e:
        return f"[fetch error: {e}]"


_CLASSIFY_SYSTEM = """You analyze web content for relevance to a documentary about Tony Scott (film director, 1944-2012).

Return ONLY valid JSON:
{
  "relevant": true|false,
  "relevance_score": 1-5,
  "source_type": "article|interview|academic|book|documentary|archive_footage|photograph|social_media|official_record|website|podcast|film",
  "topic": "biography|films|visual_style|early_career|death|criticism|legacy|relationships|personal|academic|archival|other",
  "summary": "2-3 sentences: what is this, why does it matter for the documentary",
  "key_facts": ["list of specific verifiable facts found"],
  "quotes": ["any direct quotes from Tony Scott or people who knew him"],
  "copyright_status": "public_domain|fair_use_likely|fair_use_uncertain|license_needed|official_record|creative_commons|unknown",
  "fair_use_basis": "specific basis if fair_use_likely",
  "attorney_review_needed": false,
  "notes": "any legal concerns or follow-up needed"
}

Relevance: 5=essential, 4=very useful, 3=useful, 2=marginal, 1=not useful. Only return relevant=true for score >= 3."""


def classify_source(url: str, title: str, snippet: str, full_text: str = "") -> dict | None:
    """Use Ollama to classify a source for relevance and legal status."""
    context = full_text[:3000] if full_text else snippet[:1000]
    prompt = (
        f"URL: {url}\n"
        f"Title: {title}\n"
        f"Content:\n{context}\n\n"
        f"Classify this source for the Tony Scott documentary."
    )
    try:
        result = ollama.call_json(
            prompt,
            system=_CLASSIFY_SYSTEM,
            temperature=0.1,
            max_tokens=1000,
        )
        return result if isinstance(result, dict) else None
    except Exception as e:
        log(f"  Classify error: {e}")
        return None


_SYNTHESIS_SYSTEM = """You are the lead researcher on a documentary about Tony Scott (director, 1944-2012).

Given new research findings, write a brief synthesis note:
- What new information was found this cycle?
- How does it change or add to our understanding of the documentary's themes?
- What should the filmmakers follow up on?

Keep it under 200 words. Write in plain prose, no headers."""


def synthesize_findings(new_sources: list[Source]) -> str:
    """Use Ollama to synthesize what this research cycle found."""
    if not new_sources:
        return "No new sources found this cycle."
    summaries = "\n".join(
        f"- {s.title} ({s.publisher}): {s.content_summary}"
        for s in new_sources[:10]
    )
    prompt = (
        f"New sources found this research cycle:\n{summaries}\n\n"
        f"Write a synthesis note for the documentary team."
    )
    return ollama.call(prompt, system=_SYNTHESIS_SYSTEM, temperature=0.5, max_tokens=400)

# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def run_cycle(query_index: int, reg: Registry) -> tuple[list[Source], int]:
    """Run one research cycle. Returns (new_sources, next_query_index)."""
    query_data = SEARCH_QUERIES[query_index % len(SEARCH_QUERIES)]
    query = query_data["q"]
    topic = query_data["topic"]
    next_index = (query_index + 1) % len(SEARCH_QUERIES)

    log(f"Searching [{topic}]: {query}")

    # Collect raw results from all search backends
    raw = search_ddg(query) + search_newsapi(query, 3)
    log(f"  Found {len(raw)} raw results")

    new_sources: list[Source] = []

    for item in raw:
        url = item.get("url", "").strip()
        title = item.get("title", "").strip()
        snippet = item.get("body", "").strip()

        if not url or not title:
            continue
        if reg.has_url(url):
            continue
        # Skip non-content URLs
        if any(x in url for x in ["youtube.com/watch", "twitter.com", "x.com/",
                                    "facebook.com", "instagram.com", "tiktok.com"]):
            continue

        # Fetch full text for promising results
        full_text = ""
        if len(snippet) < 200:
            full_text = fetch_text(url)

        classification = classify_source(url, title, snippet, full_text)
        if not classification or not classification.get("relevant"):
            continue

        score = classification.get("relevance_score", 1)
        if score < 3:
            continue

        s = Source(
            url=url,
            title=title,
            publisher=_extract_domain(url),
            source_type=SourceType(classification.get("source_type", "website")),
            use_type=UseType.REFERENCE,
            date_accessed=date.today().isoformat(),
            copyright_status=CopyrightStatus(
                classification.get("copyright_status", "fair_use_likely")
            ),
            fair_use_basis=classification.get("fair_use_basis", "Reference for biographical documentary"),
            attorney_review_needed=classification.get("attorney_review_needed", False),
            content_summary=classification.get("summary", snippet[:300]),
            key_facts=classification.get("key_facts", []),
            quotes=classification.get("quotes", []),
            relevance_score=score,
            notes=classification.get("notes", ""),
            added_by="research_loop",
            verified=False,
        )

        if reg.add(s):
            new_sources.append(s)
            log(f"  + NEW [{score}/5]: {title[:60]}")

    return new_sources, next_index


def _extract_domain(url: str) -> str:
    try:
        from urllib.parse import urlparse
        return urlparse(url).netloc.replace("www.", "")
    except Exception:
        return url[:50]


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Tony Scott continuous research daemon")
    parser.add_argument("--once", action="store_true",
                        help="Run one cycle and exit (for testing)")
    parser.add_argument("--interval", type=int, default=SLEEP_SECONDS,
                        help=f"Sleep seconds between cycles (default: {SLEEP_SECONDS})")
    parser.add_argument("--seed", action="store_true",
                        help="Seed registry with known sources before starting")
    args = parser.parse_args()

    # Write PID
    try:
        PID_FILE.parent.mkdir(parents=True, exist_ok=True)
        PID_FILE.write_text(str(os.getpid()))
    except Exception:
        pass

    # Graceful shutdown
    running = True
    def _stop(sig, frame):
        nonlocal running
        log("Shutdown signal received. Finishing current cycle...")
        running = False
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    # Load / seed registry
    if args.seed:
        from movie.tony_scott.sources.registry import seed_registry
        reg = seed_registry()
    else:
        reg = Registry.load()

    log(f"Research daemon started. Registry: {len(reg.sources)} sources. "
        f"Queries: {len(SEARCH_QUERIES)}. Interval: {args.interval}s.")

    query_index = 0
    cycle = 0

    while running:
        cycle += 1
        log(f"=== Cycle {cycle} | Query {query_index % len(SEARCH_QUERIES) + 1}/{len(SEARCH_QUERIES)} ===")

        try:
            new_sources, query_index = run_cycle(query_index, reg)

            if new_sources:
                reg.save()
                reg.export_legal_report()
                synthesis = synthesize_findings(new_sources)
                note = (
                    f"\n## Research Cycle {cycle} — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
                    f"**New sources:** {len(new_sources)}\n\n"
                    f"{synthesis}\n\n"
                    f"**Sources added:**\n" +
                    "".join(f"- [{s.title}]({s.url}) [{s.relevance_score}/5]\n" for s in new_sources)
                )
                append_notes(note)
                log(f"  {len(new_sources)} new sources. Registry total: {len(reg.sources)}")
            else:
                log(f"  No new sources this cycle.")

        except Exception as e:
            log(f"  ERROR in cycle: {e}")

        if args.once:
            break

        if running:
            log(f"  Sleeping {args.interval}s ...")
            # Sleep in small increments so SIGTERM is handled quickly
            for _ in range(args.interval):
                if not running:
                    break
                time.sleep(1)

    log("Research daemon stopped cleanly.")
    reg.save()
    reg.export_legal_report()


if __name__ == "__main__":
    main()
