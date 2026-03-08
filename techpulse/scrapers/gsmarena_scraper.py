"""GSMArena news scraper using httpx + BeautifulSoup."""
import time
from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup

from techpulse.config.constants import GSMARENA_NEWS_URL, SCRAPE_DELAY_SECONDS
from techpulse.scrapers.base import BaseScraper
from techpulse.utils.rate_limiter import RateLimiter


class GSMArenaScraper(BaseScraper):
    source_name = "gsmarena"

    def __init__(self):
        super().__init__()
        self._limiter = RateLimiter(calls_per_second=1.0 / SCRAPE_DELAY_SECONDS)
        self._headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/125.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        }

    def fetch(self) -> list[dict]:
        items = []
        try:
            self._limiter.wait()
            with httpx.Client(headers=self._headers, timeout=15, follow_redirects=True) as client:
                resp = client.get(GSMARENA_NEWS_URL)
                resp.raise_for_status()
                items = self._parse_news(resp.text)
        except Exception as e:
            self.logger.error(f"GSMArena fetch failed: {e}")
        return items

    def _parse_news(self, html: str) -> list[dict]:
        soup = BeautifulSoup(html, "lxml")
        items = []

        for article in soup.select("div.news-item"):
            try:
                link_tag = article.select_one("a")
                title_tag = article.select_one("h3, .news-title, a span")
                img_tag = article.select_one("img")
                time_tag = article.select_one("span.meta-info-label, time")

                if not link_tag:
                    continue

                url = link_tag.get("href", "")
                if url and not url.startswith("http"):
                    url = f"https://www.gsmarena.com/{url}"

                title = (title_tag.get_text(strip=True) if title_tag
                         else link_tag.get_text(strip=True))
                if not title:
                    continue

                external_id = url.split("/")[-1].replace(".php", "") if url else title[:50]

                published_at = datetime.now(timezone.utc).isoformat()
                if time_tag:
                    time_text = time_tag.get_text(strip=True)
                    try:
                        # GSMArena format varies; use as-is or parse
                        published_at = datetime.now(timezone.utc).isoformat()
                    except Exception:
                        pass

                items.append({
                    "external_id": f"gsma_{external_id}",
                    "content_type": "post",
                    "title": title,
                    "body": "",
                    "url": url,
                    "thumbnail_url": img_tag.get("src", "") if img_tag else "",
                    "published_at": published_at,
                })
            except Exception as e:
                self.logger.debug(f"Skipping GSMArena item: {e}")

        return items
