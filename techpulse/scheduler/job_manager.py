from __future__ import annotations
"""APScheduler setup and job registration."""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from techpulse.config.settings import settings
from techpulse.utils.logger import get_logger

logger = get_logger("scheduler")

_scheduler: BackgroundScheduler | None = None

# Callback called from UI when a scrape cycle completes
_on_scrape_done_callback = None


def set_scrape_done_callback(fn):
    global _on_scrape_done_callback
    _on_scrape_done_callback = fn


def _scrape_only():
    """Scrape all sources and notify UI — no Claude API calls."""
    from techpulse.scheduler.jobs import run_all_scrapers
    run_all_scrapers()
    if _on_scrape_done_callback:
        try:
            _on_scrape_done_callback()
        except Exception as e:
            logger.warning(f"Scrape callback error: {e}")


def _scrape_and_analyze():
    """Full cycle: scrape + Claude analysis. Used for manual refresh."""
    from techpulse.scheduler.jobs import (
        run_all_scrapers, run_sentiment_job, run_clustering_job
    )
    run_all_scrapers()
    run_sentiment_job()
    run_clustering_job()
    if _on_scrape_done_callback:
        try:
            _on_scrape_done_callback()
        except Exception as e:
            logger.warning(f"Scrape callback error: {e}")


def _daily_analysis():
    """Daily Claude analysis at 07:00 Spain time: sentiment + clustering + market intel + digest."""
    from techpulse.scheduler.jobs import (
        run_sentiment_job, run_clustering_job,
        run_daily_digest, run_weekly_digest,
        run_market_intelligence_cache,
    )
    import datetime
    logger.info("Daily analysis started (07:00 Spain)")
    run_sentiment_job()
    run_clustering_job()
    run_market_intelligence_cache()   # Fetch Amazon + Trends before digest
    run_daily_digest()
    # Weekly digest only on Mondays
    if datetime.datetime.now().weekday() == 0:
        run_weekly_digest()
    if _on_scrape_done_callback:
        try:
            _on_scrape_done_callback()
        except Exception as e:
            logger.warning(f"Analysis callback error: {e}")
    logger.info("Daily analysis complete")


def start_scheduler():
    global _scheduler
    if _scheduler and _scheduler.running:
        return

    _scheduler = BackgroundScheduler(daemon=True)

    # Scraping every N hours — no Claude API cost
    _scheduler.add_job(
        _scrape_only,
        trigger=IntervalTrigger(hours=settings.SCRAPE_INTERVAL_HOURS),
        id="scrape_cycle",
        name="Scrape (no analysis)",
        replace_existing=True,
        misfire_grace_time=300,
    )

    # Claude analysis once a day at 07:00 Spain time (Europe/Madrid)
    _scheduler.add_job(
        _daily_analysis,
        trigger=CronTrigger(hour=7, minute=0, timezone="Europe/Madrid"),
        id="daily_analysis",
        name="Daily Claude Analysis",
        replace_existing=True,
        misfire_grace_time=600,
    )

    _scheduler.start()
    logger.info(
        f"Scheduler started. Scrape: every {settings.SCRAPE_INTERVAL_HOURS}h | "
        f"Analysis: daily at 07:00 Europe/Madrid"
    )


def stop_scheduler():
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")


def trigger_now():
    """Manually trigger a scrape cycle immediately."""
    import threading
    thread = threading.Thread(target=_scrape_and_analyze, daemon=True, name="manual_scrape")
    thread.start()
    logger.info("Manual scrape triggered")


def get_next_run() -> str | None:
    """Return ISO string of next scheduled analysis (07:00 Spain), or None."""
    if not _scheduler:
        return None
    job = _scheduler.get_job("daily_analysis")
    if job and job.next_run_time:
        return job.next_run_time.isoformat()
    return None
