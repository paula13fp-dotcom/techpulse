from __future__ import annotations
"""Reddit scraper — uses old.reddit.com JSON endpoints (no API key required).

old.reddit.com is more permissive with server-side requests than www.reddit.com
which aggressively blocks non-browser traffic from cloud IPs.
"""
import time
from datetime import datetime, timezone

import httpx

from techpulse.config.settings import settings
from techpulse.config.constants import SUBREDDITS
from techpulse.scrapers.base import BaseScraper
from techpulse.utils.rate_limiter import RateLimiter

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,es;q=0.8",
}


class RedditScraper(BaseScraper):
    source_name = "reddit"

    def __init__(self):
        super().__init__()
        self._limiter = RateLimiter(calls_per_second=0.5)  # 1 req / 2s

    def fetch(self) -> list[dict]:
        items = []
        limit = min(25, max(10, settings.MAX_POSTS_PER_RUN // 3))

        all_subs: list[str] = []
        for subs in SUBREDDITS.values():
            all_subs.extend(subs)
        # Deduplicate preserving order
        seen: set[str] = set()
        unique_subs = [s for s in all_subs if not (s in seen or seen.add(s))]

        with httpx.Client(headers=_HEADERS, timeout=15, follow_redirects=True) as client:
            for sub in unique_subs:
                try:
                    self._limiter.wait()
                    posts = self._fetch_sub(client, sub, limit)
                    items.extend(posts)
                    self.logger.debug(f"r/{sub}: {len(posts)} posts")
                except Exception as e:
                    self.logger.warning(f"r/{sub} failed: {e}")

        return items

    def _fetch_sub(self, client: httpx.Client, sub: str, limit: int) -> list[dict]:
        # Use old.reddit.com — much less aggressive blocking of server IPs
        url = f"https://old.reddit.com/r/{sub}/hot.json?limit={limit}&raw_json=1"
        resp = client.get(url)

        # Reddit sometimes returns HTML login page instead of JSON
        content_type = resp.headers.get("content-type", "")
        if "json" not in content_type:
            self.logger.warning(f"r/{sub}: got non-JSON response ({content_type})")
            return []

        resp.raise_for_status()
        data = resp.json()

        posts = []
        for child in data.get("data", {}).get("children", []):
            post = child.get("data", {})
            if not post:
                continue
            normalized = self._normalize(post)
            if normalized:
                posts.append(normalized)
        return posts

    def _normalize(self, post: dict) -> dict | None:
        post_id = post.get("id")
        if not post_id:
            return None

        created = post.get("created_utc", 0)
        published_at = datetime.fromtimestamp(created, tz=timezone.utc).isoformat()

        return {
            "external_id": post_id,
            "content_type": "post",
            "title": post.get("title", ""),
            "body": post.get("selftext", "") or "",
            "author": post.get("author", "[deleted]"),
            "url": f"https://reddit.com{post.get('permalink', '')}",
            "upvotes": post.get("ups", 0),
            "score": post.get("score", 0),
            "comment_count": post.get("num_comments", 0),
            "view_count": post.get("view_count") or 0,
            "published_at": published_at,
        }
