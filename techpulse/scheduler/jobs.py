"""Scheduled job functions called by APScheduler."""
from __future__ import annotations
import json
import os
import time as _time
from datetime import datetime, timezone
from pathlib import Path

from techpulse.utils.logger import get_logger

logger = get_logger("scheduler.jobs")

# Path to the shared market intelligence cache file
_DATA_DIR  = Path(__file__).parent.parent / "data"
_CACHE_FILE = _DATA_DIR / "market_cache.json"


def run_all_scrapers():
    """Run all configured scrapers sequentially."""
    from techpulse.scrapers.reddit_scraper import RedditScraper
    from techpulse.scrapers.youtube_scraper import YouTubeScraper
    from techpulse.scrapers.xda_scraper import XDAScraper
    from techpulse.scrapers.gsmarena_scraper import GSMArenaScraper
    from techpulse.scrapers.tiktok_scraper import TikTokScraper
    from techpulse.scrapers.x_scraper import XScraper
    from techpulse.scrapers.techblogs_scraper import (
        # Blogs ES (originales)
        XatakaScraper, XatakaMovilScraper, MuyComputerScraper,
        Andro4allScraper, HipertextualScraper, ApplesferaScraper,
        # Blogs ES (nuevos)
        HardzoneScraper, TuExpertoScraper, IPhonerosScraper,
        # Leaks/rumores EN (nuevos)
        NineToFiveMacScraper, NineToFiveGoogleScraper, MacRumorsScraper,
        AndroidAuthorityScraper, WccftechScraper, TheVergeScraper,
        SamMobileScraper, AndroidPoliceScraper, PhandroidScraper, TechRadarScraper,
    )

    scrapers = [
        RedditScraper(),
        YouTubeScraper(),
        XDAScraper(),
        GSMArenaScraper(),
        TikTokScraper(),
        XScraper(),
        # Blogs ES
        XatakaScraper(),
        XatakaMovilScraper(),
        MuyComputerScraper(),
        Andro4allScraper(),
        HipertextualScraper(),
        ApplesferaScraper(),
        HardzoneScraper(),
        TuExpertoScraper(),
        IPhonerosScraper(),
        # Leaks/rumores EN
        NineToFiveMacScraper(),
        NineToFiveGoogleScraper(),
        MacRumorsScraper(),
        AndroidAuthorityScraper(),
        WccftechScraper(),
        TheVergeScraper(),
        SamMobileScraper(),
        AndroidPoliceScraper(),
        PhandroidScraper(),
        TechRadarScraper(),
    ]

    total = 0
    for scraper in scrapers:
        try:
            count = scraper.run()
            total += count
        except Exception as e:
            logger.error(f"Scraper {scraper.source_name} crashed: {e}")

    logger.info(f"Scrape cycle complete: {total} new posts")
    return total


def run_sentiment_job():
    """Run sentiment analysis on unanalyzed posts."""
    from techpulse.analysis.sentiment import run_sentiment_analysis
    try:
        return run_sentiment_analysis(limit=200)
    except Exception as e:
        logger.error(f"Sentiment job failed: {e}")
        return 0


def run_clustering_job():
    """Run topic clustering on recent posts."""
    from techpulse.analysis.clustering import run_clustering
    try:
        return run_clustering(days_back=3)
    except Exception as e:
        logger.error(f"Clustering job failed: {e}")
        return 0


def run_daily_digest():
    """Generate daily digest."""
    from techpulse.analysis.digest import run_digest
    try:
        return run_digest(digest_type="daily")
    except Exception as e:
        logger.error(f"Daily digest failed: {e}")
        return None


def run_weekly_digest():
    """Generate weekly digest."""
    from techpulse.analysis.digest import run_digest
    try:
        return run_digest(digest_type="weekly")
    except Exception as e:
        logger.error(f"Weekly digest failed: {e}")
        return None


def run_market_intelligence_cache() -> dict:
    """Fetch Amazon bestsellers + novedades for all 5 categories.

    Google Trends is excluded from the automatic pipeline because the pytrends
    batch mode consistently triggers Google's 429 rate-limiter. Trends data is
    still available for manual consultation in the Tendencias Búsqueda page.

    Saves results to techpulse/data/market_cache.json so the Streamlit UI and
    digest generator can read fresh data without triggering a new scrape.

    Returns:
        dict with keys "categories", "errors"
    """
    from techpulse.scrapers.amazon_scraper import (
        get_bestsellers, get_new_releases, CATEGORY_LABELS,
    )

    _DATA_DIR.mkdir(parents=True, exist_ok=True)

    cache: dict = {
        "updated_at":          datetime.now(timezone.utc).isoformat(),
        "amazon_bestsellers":  {},
        "amazon_new_releases": {},
        "google_trends":       {},   # populated only via manual UI refresh
    }
    errors: list[str] = []

    # ── Amazon bestsellers + novedades ────────────────────────────────────────
    for cat in CATEGORY_LABELS:
        # Bestsellers
        try:
            prods, err = get_bestsellers(cat, limit=5)
            if err:
                errors.append(f"bestsellers/{cat}: {err}")
            cache["amazon_bestsellers"][cat] = [
                {"rank": p.rank, "title": p.title, "price": p.price, "rating": p.rating}
                for p in prods
            ]
        except Exception as e:
            errors.append(f"bestsellers/{cat}: {e}")
            cache["amazon_bestsellers"][cat] = []

        # New releases
        try:
            prods, err = get_new_releases(cat, limit=5)
            if err:
                errors.append(f"new-releases/{cat}: {err}")
            cache["amazon_new_releases"][cat] = [
                {"rank": p.rank, "title": p.title, "price": p.price, "rating": p.rating}
                for p in prods
            ]
        except Exception as e:
            errors.append(f"new-releases/{cat}: {e}")
            cache["amazon_new_releases"][cat] = []

    # ── Write cache ───────────────────────────────────────────────────────────
    try:
        _CACHE_FILE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info(f"Market intelligence cache saved → {_CACHE_FILE}")
    except Exception as e:
        errors.append(f"write cache: {e}")
        logger.error(f"Failed to write market cache: {e}")

    if errors:
        logger.warning(f"Market intelligence cache had {len(errors)} errors: {errors[:3]}")

    return {"categories": len(CATEGORY_LABELS), "errors": errors}


def load_market_cache() -> dict | None:
    """Load market_cache.json if it exists and is < 25 hours old. Returns None otherwise."""
    if not _CACHE_FILE.exists():
        return None
    try:
        data = json.loads(_CACHE_FILE.read_text(encoding="utf-8"))
        updated = datetime.fromisoformat(data.get("updated_at", "2000-01-01T00:00:00+00:00"))
        age_hours = (datetime.now(timezone.utc) - updated).total_seconds() / 3600
        if age_hours > 25:
            return None
        return data
    except Exception:
        return None


def run_full_pipeline() -> dict:
    """Complete pipeline: scrapers + sentiment + clustering + market intel + digest.

    Returns:
        dict with keys "posts", "sentiment", "clusters"
    """
    logger.info("Full pipeline started")
    posts  = run_all_scrapers()
    sent   = run_sentiment_job()
    clust  = run_clustering_job()
    run_market_intelligence_cache()
    run_daily_digest()
    logger.info(f"Full pipeline complete: {posts} posts, {sent} analysed, {clust} clusters")
    return {"posts": posts, "sentiment": sent, "clusters": clust}
