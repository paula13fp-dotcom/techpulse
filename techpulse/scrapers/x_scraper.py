"""X (Twitter) scraper using twikit (async, cookie-based auth).

Searches for tech-related tweets by keyword and monitors key leaker/reviewer
accounts. Requires X_USERNAME, X_EMAIL, X_PASSWORD in environment.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone, timedelta
from pathlib import Path

from techpulse.config.settings import settings
from techpulse.config.constants import X_QUERIES, X_ACCOUNTS, X_SEARCHES_PER_RUN
from techpulse.scrapers.base import BaseScraper

_COOKIE_PATH = Path(__file__).resolve().parents[1] / "data" / "x_cookies.json"
_COOKIE_MAX_AGE_HOURS = 23


class XScraper(BaseScraper):
    source_name = "x"

    def __init__(self):
        super().__init__()
        if not settings.has_x():
            self.logger.warning("X credentials not configured — scraper disabled")

    def fetch(self) -> list[dict]:
        if not settings.has_x():
            return []
        try:
            return asyncio.run(self._fetch_async())
        except Exception as e:
            self.logger.error(f"X scraper failed: {e}")
            return []

    async def _fetch_async(self) -> list[dict]:
        try:
            from twikit import Client
        except ImportError:
            self.logger.warning("twikit not installed — skipping X")
            return []

        client = Client("en-US")

        # Attempt to load saved cookies; fall back to fresh login
        if self._cookies_valid():
            try:
                client.load_cookies(_COOKIE_PATH)
                self.logger.info("Loaded saved X cookies")
            except Exception:
                await self._login(client)
        else:
            await self._login(client)

        items: list[dict] = []

        # ── 1) Search by keyword queries ─────────────────────────────────────
        all_queries: list[str] = []
        for queries in X_QUERIES.values():
            all_queries.extend(queries)
        # Limit to avoid rate-limit exhaustion
        all_queries = all_queries[:X_SEARCHES_PER_RUN]

        for query in all_queries:
            try:
                tweets = await client.search_tweet(query, product="Latest", count=10)
                for tweet in tweets:
                    normalized = self._normalize_tweet(tweet)
                    if normalized:
                        items.append(normalized)
            except Exception as e:
                self.logger.warning(f"X search '{query}' failed: {e}")

        # ── 2) Fetch user timelines ──────────────────────────────────────────
        for username in X_ACCOUNTS:
            try:
                user = await client.get_user_by_screen_name(username)
                if user:
                    tweets = await client.get_user_tweets(user.id, tweet_type="Tweets", count=10)
                    for tweet in tweets:
                        normalized = self._normalize_tweet(tweet)
                        if normalized:
                            items.append(normalized)
            except Exception as e:
                self.logger.warning(f"X user @{username} failed: {e}")

        # Deduplicate by external_id
        seen: set[str] = set()
        unique: list[dict] = []
        for item in items:
            if item["external_id"] not in seen:
                seen.add(item["external_id"])
                unique.append(item)

        self.logger.info(f"X scraper fetched {len(unique)} unique tweets")
        return unique

    async def _login(self, client):
        """Login to X and save cookies for reuse."""
        await client.login(
            auth_info_1=settings.X_USERNAME,
            auth_info_2=settings.X_EMAIL,
            password=settings.X_PASSWORD,
        )
        try:
            _COOKIE_PATH.parent.mkdir(parents=True, exist_ok=True)
            client.save_cookies(_COOKIE_PATH)
            self.logger.info("Saved X cookies for reuse")
        except Exception as e:
            self.logger.warning(f"Could not save X cookies: {e}")

    def _cookies_valid(self) -> bool:
        """Check if saved cookies exist and are less than 23 hours old."""
        if not _COOKIE_PATH.exists():
            return False
        try:
            age = datetime.now() - datetime.fromtimestamp(_COOKIE_PATH.stat().st_mtime)
            return age < timedelta(hours=_COOKIE_MAX_AGE_HOURS)
        except Exception:
            return False

    def _normalize_tweet(self, tweet) -> dict | None:
        """Convert a twikit tweet object to the standard normalized dict."""
        tweet_id = getattr(tweet, "id", None)
        if not tweet_id:
            return None
        tweet_id = str(tweet_id)

        author = "unknown"
        if hasattr(tweet, "user") and tweet.user:
            author = getattr(tweet.user, "screen_name", "unknown")

        text = getattr(tweet, "full_text", "") or getattr(tweet, "text", "") or ""

        # Parse published_at from tweet.created_at (Twitter date format)
        published_at = datetime.now(timezone.utc).isoformat()
        created_at = getattr(tweet, "created_at", None)
        if created_at:
            try:
                from email.utils import parsedate_to_datetime
                published_at = parsedate_to_datetime(created_at).isoformat()
            except Exception:
                pass

        return {
            "external_id": f"x_{tweet_id}",
            "content_type": "post",
            "title": text[:200],
            "body": text,
            "author": f"@{author}",
            "url": f"https://x.com/{author}/status/{tweet_id}",
            "thumbnail_url": "",
            "view_count": getattr(tweet, "view_count", 0) or 0,
            "like_count": getattr(tweet, "favorite_count", 0) or 0,
            "share_count": getattr(tweet, "retweet_count", 0) or 0,
            "comment_count": getattr(tweet, "reply_count", 0) or 0,
            "published_at": published_at,
        }
