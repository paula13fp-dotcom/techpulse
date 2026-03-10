"""TikTok scraper — HTTP-only (cloud-compatible, no Playwright).

Fetches TikTok hashtag pages and extracts embedded JSON data
(__UNIVERSAL_DATA_FOR_REHYDRATION__) to get video metadata.
This approach avoids any browser/Playwright dependency but may
break if TikTok changes their page structure.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup

from techpulse.config.constants import TIKTOK_HASHTAGS
from techpulse.config.settings import settings
from techpulse.scrapers.base import BaseScraper
from techpulse.utils.rate_limiter import RateLimiter


class TikTokScraper(BaseScraper):
    source_name = "tiktok"

    def __init__(self):
        super().__init__()
        self._limiter = RateLimiter(calls_per_second=0.33)  # ~1 req per 3s
        self._headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml",
        }

    def fetch(self) -> list[dict]:
        items: list[dict] = []
        all_tags: list[str] = []
        for tags in TIKTOK_HASHTAGS.values():
            all_tags.extend(tags)
        # Deduplicate preserving order
        all_tags = list(dict.fromkeys(all_tags))[:10]

        with httpx.Client(
            headers=self._headers, timeout=20, follow_redirects=True
        ) as client:
            for hashtag in all_tags:
                try:
                    self._limiter.wait()
                    videos = self._fetch_hashtag(client, hashtag)
                    items.extend(videos)
                    self.logger.debug(f"TikTok #{hashtag}: {len(videos)} videos")
                except Exception as e:
                    self.logger.warning(f"TikTok #{hashtag} failed: {e}")

        self.logger.info(f"TikTok scraper fetched {len(items)} videos")
        return items

    def _fetch_hashtag(self, client: httpx.Client, hashtag: str) -> list[dict]:
        """Fetch a TikTok hashtag page and extract video metadata."""
        url = f"https://www.tiktok.com/tag/{hashtag}"
        resp = client.get(url)
        resp.raise_for_status()
        return self._parse_rehydration_data(resp.text)

    def _parse_rehydration_data(self, html: str) -> list[dict]:
        """Extract video data from __UNIVERSAL_DATA_FOR_REHYDRATION__ JSON."""
        soup = BeautifulSoup(html, "lxml")
        script_tag = soup.find("script", id="__UNIVERSAL_DATA_FOR_REHYDRATION__")
        if not script_tag or not script_tag.string:
            # Try alternative: SIGI_STATE embedded JSON
            script_tag = soup.find("script", id="SIGI_STATE")
            if not script_tag or not script_tag.string:
                self.logger.debug("No rehydration data found in TikTok page")
                return []

        try:
            data = json.loads(script_tag.string)
        except json.JSONDecodeError:
            self.logger.debug("Failed to parse TikTok rehydration JSON")
            return []

        items: list[dict] = []
        try:
            # Navigate nested structure — TikTok changes paths occasionally
            default_scope = data.get("__DEFAULT_SCOPE__", {})
            detail = (
                default_scope.get("webapp.hashtag-detail", {})
                or default_scope.get("webapp.search-detail", {})
                or {}
            )
            item_list = detail.get("itemList", [])

            # Fallback: try SIGI_STATE structure
            if not item_list:
                item_module = data.get("ItemModule", {})
                if item_module:
                    item_list = list(item_module.values())

            limit = max(5, settings.MAX_POSTS_PER_RUN // 10)
            for video in item_list[:limit]:
                normalized = self._normalize_video(video)
                if normalized:
                    items.append(normalized)
        except Exception as e:
            self.logger.warning(f"Failed to extract TikTok videos: {e}")

        return items

    def _normalize_video(self, video: dict) -> dict | None:
        """Convert a TikTok video dict to the standard normalized format."""
        vid_id = str(video.get("id", ""))
        if not vid_id:
            return None

        author_info = video.get("author", {})
        if isinstance(author_info, dict):
            author = author_info.get("uniqueId", "unknown")
        else:
            author = str(author_info) if author_info else "unknown"

        desc = video.get("desc", "")
        stats = video.get("stats", {})

        published_at = datetime.now(timezone.utc).isoformat()
        create_time = video.get("createTime")
        if create_time:
            try:
                published_at = datetime.fromtimestamp(
                    int(create_time), tz=timezone.utc
                ).isoformat()
            except (ValueError, TypeError):
                pass

        return {
            "external_id": f"tt_{vid_id}",
            "content_type": "short",
            "title": desc[:200],
            "body": desc,
            "author": author,
            "url": f"https://www.tiktok.com/@{author}/video/{vid_id}",
            "thumbnail_url": video.get("video", {}).get("cover", "") if isinstance(video.get("video"), dict) else "",
            "view_count": int(stats.get("playCount", 0) or 0),
            "like_count": int(stats.get("diggCount", 0) or 0),
            "share_count": int(stats.get("shareCount", 0) or 0),
            "comment_count": int(stats.get("commentCount", 0) or 0),
            "published_at": published_at,
        }
