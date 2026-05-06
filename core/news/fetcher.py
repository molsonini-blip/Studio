from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

import feedparser
import httpx
import trafilatura
import yaml

from core.news.models import RawArticle

_CFG_PATH = Path(__file__).resolve().parents[2] / "config" / "settings.yaml"


def _news_cfg() -> dict:
    with open(_CFG_PATH) as f:
        return yaml.safe_load(f).get("news", {})


# ── RSS sources (free, no API key) ────────────────────────────────────────────

RSS_FEEDS: dict[str, str] = {
    "AP News":         "https://feeds.apnews.com/rss/apf-topnews",
    "Reuters":         "https://feeds.reuters.com/reuters/topNews",
    "BBC":             "https://feeds.bbci.co.uk/news/rss.xml",
    "NPR":             "https://feeds.npr.org/1001/rss.xml",
    "CBS News":        "https://www.cbsnews.com/latest/rss/main",
    "ABC News":        "https://feeds.abcnews.com/abcnews/topstories",
    "USA Today":       "https://rssfeeds.usatoday.com/usatoday-NewsTopStories",
}


def fetch_rss(max_per_feed: int = 5) -> list[RawArticle]:
    articles: list[RawArticle] = []
    for source, url in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:max_per_feed]:
                pub = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    try:
                        pub = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                    except Exception:
                        pass
                articles.append(RawArticle(
                    title=entry.get("title", "").strip(),
                    url=entry.get("link", ""),
                    source=source,
                    published=pub,
                    summary=entry.get("summary", "").strip(),
                ))
        except Exception:
            continue
    return articles


# ── NewsAPI ───────────────────────────────────────────────────────────────────

def fetch_newsapi(query: str = "", category: str = "general", page_size: int = 20) -> list[RawArticle]:
    api_key = os.environ.get("NEWSAPI_KEY", "")
    if not api_key:
        return []
    params: dict = {"pageSize": page_size, "language": "en", "apiKey": api_key}
    if query:
        url = "https://newsapi.org/v2/everything"
        params["q"] = query
        params["sortBy"] = "publishedAt"
    else:
        url = "https://newsapi.org/v2/top-headlines"
        params["category"] = category
        params["country"] = "us"

    try:
        resp = httpx.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return []

    articles = []
    for item in data.get("articles", []):
        pub = None
        try:
            pub = datetime.fromisoformat(item["publishedAt"].replace("Z", "+00:00"))
        except Exception:
            pass
        articles.append(RawArticle(
            title=item.get("title", "").strip(),
            url=item.get("url", ""),
            source=item.get("source", {}).get("name", "NewsAPI"),
            published=pub,
            summary=item.get("description", "").strip(),
            category=category,
        ))
    return articles


# ── GNews ─────────────────────────────────────────────────────────────────────

def fetch_gnews(query: str = "", max_articles: int = 10) -> list[RawArticle]:
    api_key = os.environ.get("GNEWS_KEY", "")
    if not api_key:
        return []
    params = {"token": api_key, "lang": "en", "max": max_articles}
    url = "https://gnews.io/api/v4/search" if query else "https://gnews.io/api/v4/top-headlines"
    if query:
        params["q"] = query

    try:
        resp = httpx.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return []

    articles = []
    for item in data.get("articles", []):
        pub = None
        try:
            pub = datetime.fromisoformat(item["publishedAt"].replace("Z", "+00:00"))
        except Exception:
            pass
        articles.append(RawArticle(
            title=item.get("title", "").strip(),
            url=item.get("url", ""),
            source=item.get("source", {}).get("name", "GNews"),
            published=pub,
            summary=item.get("description", "").strip(),
        ))
    return articles


# ── Full-text extraction ──────────────────────────────────────────────────────

def enrich_full_text(article: RawArticle, timeout: int = 10) -> RawArticle:
    """Fetch and extract clean article body from the article URL."""
    if not article.url:
        return article
    try:
        downloaded = trafilatura.fetch_url(article.url)
        if downloaded:
            text = trafilatura.extract(
                downloaded,
                include_comments=False,
                include_tables=False,
                no_fallback=False,
            )
            if text:
                article.full_text = text.strip()
    except Exception:
        pass
    return article


# ── Combined fetch ────────────────────────────────────────────────────────────

def fetch_articles(
    query: str = "",
    category: str = "general",
    sources: list[str] | None = None,
    max_articles: int = 20,
    enrich: bool = True,
) -> list[RawArticle]:
    """Pull from all available sources and optionally enrich with full text."""
    use = set(sources or ["rss", "newsapi", "gnews"])
    articles: list[RawArticle] = []

    if "rss" in use:
        articles += fetch_rss(max_per_feed=3)
    if "newsapi" in use:
        articles += fetch_newsapi(query=query, category=category)
    if "gnews" in use:
        articles += fetch_gnews(query=query)

    # Deduplicate by URL
    seen: set[str] = set()
    unique: list[RawArticle] = []
    for a in articles:
        if a.url and a.url not in seen:
            seen.add(a.url)
            unique.append(a)

    # Sort newest first
    unique.sort(key=lambda a: a.published or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    unique = unique[:max_articles]

    if enrich:
        for a in unique:
            enrich_full_text(a)

    return unique
