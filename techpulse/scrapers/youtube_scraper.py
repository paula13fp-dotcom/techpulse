"""YouTube scraper using the official Data API v3."""
from datetime import datetime, timezone, timedelta

from googleapiclient.discovery import build

from techpulse.config.settings import settings
from techpulse.config.constants import YOUTUBE_QUERIES
from techpulse.scrapers.base import BaseScraper


class YouTubeScraper(BaseScraper):
    source_name = "youtube"

    def __init__(self):
        super().__init__()
        if not settings.has_youtube():
            self.logger.warning("YouTube API key not configured — scraper disabled")
            self._service = None
            return
        self._service = build("youtube", "v3", developerKey=settings.YOUTUBE_API_KEY)

    def fetch(self) -> list[dict]:
        if not self._service:
            return []

        items = []
        published_after = (
            datetime.now(timezone.utc) - timedelta(days=7)
        ).strftime("%Y-%m-%dT%H:%M:%SZ")

        # Limit queries to stay within daily quota (100 units/search)
        max_queries = min(30, settings.MAX_POSTS_PER_RUN // 3)
        query_list = []
        for queries in YOUTUBE_QUERIES.values():
            query_list.extend(queries)
        query_list = query_list[:max_queries]

        for query in query_list:
            try:
                results = self._search_videos(query, published_after)
                items.extend(results)
            except Exception as e:
                self.logger.warning(f"YouTube query '{query}' failed: {e}")

        return items

    def _search_videos(self, query: str, published_after: str) -> list[dict]:
        response = self._service.search().list(
            part="snippet",
            q=query,
            type="video",
            publishedAfter=published_after,
            maxResults=10,
            relevanceLanguage="en",
            order="relevance",
        ).execute()

        video_ids = [item["id"]["videoId"] for item in response.get("items", [])]
        if not video_ids:
            return []

        # Get statistics in a single batch call
        stats_response = self._service.videos().list(
            part="statistics,snippet",
            id=",".join(video_ids),
        ).execute()

        items = []
        for video in stats_response.get("items", []):
            snippet = video["snippet"]
            stats = video.get("statistics", {})
            published = snippet.get("publishedAt", "")
            items.append({
                "external_id": video["id"],
                "content_type": "video",
                "title": snippet.get("title", ""),
                "body": snippet.get("description", ""),
                "author": snippet.get("channelTitle", ""),
                "url": f"https://www.youtube.com/watch?v={video['id']}",
                "thumbnail_url": snippet.get("thumbnails", {}).get("medium", {}).get("url", ""),
                "view_count": int(stats.get("viewCount", 0)),
                "like_count": int(stats.get("likeCount", 0)),
                "comment_count": int(stats.get("commentCount", 0)),
                "published_at": published,
            })
        return items
