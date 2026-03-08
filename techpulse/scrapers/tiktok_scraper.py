"""TikTok scraper using the unofficial TikTokApi (Playwright-based).

Note: TikTok has no official public API. This scraper uses the TikTokApi
library which operates headlessly. It may break if TikTok changes their
anti-bot measures. Failures are caught gracefully.
"""
import asyncio
from datetime import datetime, timezone

from techpulse.config.constants import TIKTOK_HASHTAGS
from techpulse.config.settings import settings
from techpulse.scrapers.base import BaseScraper


class TikTokScraper(BaseScraper):
    source_name = "tiktok"

    def fetch(self) -> list[dict]:
        try:
            return asyncio.run(self._fetch_async())
        except Exception as e:
            self.logger.error(f"TikTok scraper failed: {e}")
            return []

    async def _fetch_async(self) -> list[dict]:
        try:
            from TikTokApi import TikTokApi
        except ImportError:
            self.logger.warning("TikTokApi not installed — skipping TikTok")
            return []

        items = []
        limit_per_tag = max(5, settings.MAX_POSTS_PER_RUN // 10)

        all_tags = []
        for tags in TIKTOK_HASHTAGS.values():
            all_tags.extend(tags)
        # Deduplicate
        all_tags = list(dict.fromkeys(all_tags))[:10]

        async with TikTokApi() as api:
            await api.create_sessions(
                ms_tokens=[None],  # No token needed for public content
                num_sessions=1,
                sleep_after=3,
                headless=True,
            )
            for hashtag in all_tags:
                try:
                    tag = api.hashtag(name=hashtag)
                    async for video in tag.videos(count=limit_per_tag):
                        items.append(self._normalize_video(video))
                except Exception as e:
                    self.logger.warning(f"TikTok hashtag #{hashtag} failed: {e}")

        return items

    def _normalize_video(self, video) -> dict:
        vid_id = str(video.id)
        author = video.author.unique_id if video.author else "unknown"
        desc = video.desc if hasattr(video, "desc") else ""
        stats = video.stats if hasattr(video, "stats") else {}

        published_at = datetime.now(timezone.utc).isoformat()
        if hasattr(video, "create_time") and video.create_time:
            published_at = datetime.fromtimestamp(
                video.create_time, tz=timezone.utc
            ).isoformat()

        return {
            "external_id": f"tt_{vid_id}",
            "content_type": "short",
            "title": desc[:200],
            "body": desc,
            "author": author,
            "url": f"https://www.tiktok.com/@{author}/video/{vid_id}",
            "view_count": getattr(stats, "play_count", 0) if stats else 0,
            "like_count": getattr(stats, "digg_count", 0) if stats else 0,
            "share_count": getattr(stats, "share_count", 0) if stats else 0,
            "comment_count": getattr(stats, "comment_count", 0) if stats else 0,
            "published_at": published_at,
        }
