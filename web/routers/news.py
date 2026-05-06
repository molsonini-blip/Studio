from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from core.news.fetcher import fetch_articles
from core.news.models import ProcessedScript, RawArticle
from core.news.processor import process_article

router = APIRouter()


# ── Response models ───────────────────────────────────────────────────────────

class ArticleOut(BaseModel):
    title: str
    url: str
    source: str
    published: str | None
    summary: str
    has_full_text: bool


class ScriptOut(BaseModel):
    headline: str
    anchor_script: str
    sentences: list[str]
    srt: str
    word_count: int
    estimated_duration_sec: float
    source_url: str
    source_name: str
    original_title: str


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/headlines", response_model=list[ArticleOut])
def get_headlines(
    query: str = Query("", description="Keyword search (blank = top headlines)"),
    category: str = Query("general", description="general|business|technology|science|health|sports|entertainment"),
    sources: str = Query("rss,newsapi,gnews", description="Comma-separated: rss, newsapi, gnews"),
    max_articles: int = Query(20, ge=1, le=50),
    enrich: bool = Query(False, description="Fetch full article text (slower)"),
):
    source_list = [s.strip() for s in sources.split(",")]
    try:
        articles = fetch_articles(
            query=query,
            category=category,
            sources=source_list,
            max_articles=max_articles,
            enrich=enrich,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return [
        ArticleOut(
            title=a.title,
            url=a.url,
            source=a.source,
            published=a.published.isoformat() if a.published else None,
            summary=a.summary,
            has_full_text=bool(a.full_text),
        )
        for a in articles
    ]


@router.post("/process", response_model=ScriptOut)
def process_url(
    url: str = Query(..., description="Article URL to fetch, clean, and script"),
):
    """Fetch a single article by URL, strip bias, and return a broadcast-ready script."""
    from core.news.fetcher import enrich_full_text
    from core.news.models import RawArticle as _RA

    article = _RA(title="", url=url, source="", published=None)
    article = enrich_full_text(article)
    if not article.full_text:
        raise HTTPException(status_code=422, detail="Could not extract article text from URL.")

    # Use trafilatura-extracted title if available
    if not article.title:
        article.title = url

    try:
        script = process_article(article)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM processing failed: {e}")

    return ScriptOut(
        headline=script.headline,
        anchor_script=script.anchor_script,
        sentences=script.sentences,
        srt=script.srt,
        word_count=script.word_count,
        estimated_duration_sec=script.estimated_duration_sec,
        source_url=script.source_url,
        source_name=script.source_name,
        original_title=script.original_title,
    )


@router.post("/process-batch", response_model=list[ScriptOut])
def process_batch(
    query: str = Query("", description="Keyword search"),
    category: str = Query("general"),
    max_articles: int = Query(5, ge=1, le=20),
):
    """Fetch top headlines, enrich full text, and process all through the LLM."""
    try:
        articles = fetch_articles(
            query=query, category=category,
            max_articles=max_articles, enrich=True,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    results = []
    for article in articles:
        if not (article.full_text or article.summary):
            continue
        try:
            script = process_article(article)
            results.append(ScriptOut(
                headline=script.headline,
                anchor_script=script.anchor_script,
                sentences=script.sentences,
                srt=script.srt,
                word_count=script.word_count,
                estimated_duration_sec=script.estimated_duration_sec,
                source_url=script.source_url,
                source_name=script.source_name,
                original_title=script.original_title,
            ))
        except Exception:
            continue

    return results


@router.get("/srt/{job_id}", response_class=PlainTextResponse)
def get_srt(job_id: str):
    """Return SRT caption file for a previously processed script (stub — extend with job store)."""
    raise HTTPException(status_code=404, detail="Job store not yet implemented. Use /process directly.")
