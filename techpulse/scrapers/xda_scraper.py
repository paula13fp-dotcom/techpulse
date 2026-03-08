"""XDA Developers news scraper using httpx + BeautifulSoup."""
from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup

from techpulse.config.constants import SCRAPE_DELAY_SECONDS
from techpulse.scrapers.base import BaseScraper
from techpulse.utils.rate_limiter import RateLimiter

XDA_NEWS_URL = "https://www.xda-developers.com/feed/"
XDA_BASE = "https://www.xda-developers.com"


class XDAScraper(BaseScraper):
    source_name = "xda"

    def __init__(self):
        super().__init__()
        self._limiter = RateLimiter(calls_per_second=1.0 / SCRAPE_DELAY_SECONDS)
        self._headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/125.0.0.0 Safari/537.36",
        }

    def fetch(self) -> list[dict]:
        items = []
        try:
            self._limiter.wait()
            with httpx.Client(headers=self._headers, timeout=15, follow_redirects=True) as client:
                resp = client.get(XDA_NEWS_URL)
                resp.raise_for_status()
                items = self._parse_rss(resp.text)
        except Exception as e:
            self.logger.error(f"XDA fetch failed: {e}")
        return items

    def _parse_rss(self, xml: str) -> list[dict]:
        soup = BeautifulSoup(xml, "xml")
        items = []

        for item in soup.find_all("item"):
            try:
                title = item.find("title")
                link = item.find("link")
                description = item.find("description")
                pub_date = item.find("pubDate")
                guid = item.find("guid")

                title_text = title.get_text(strip=True) if title else ""
                url = link.get_text(strip=True) if link else ""
                body = description.get_text(strip=True) if description else ""
                external_id = guid.get_text(strip=True) if guid else url

                # Parse publication date
                published_at = datetime.now(timezone.utc).isoformat()
                if pub_date:
                    try:
                        from email.utils import parsedate_to_datetime
                        published_at = parsedate_to_datetime(
                            pub_date.get_text(strip=True)
                        ).isoformat()
                    except Exception:
                        pass

                # Extract image from description HTML
                thumbnail = ""
                if description:
                    desc_soup = BeautifulSoup(description.get_text(), "html.parser")
                    img = desc_soup.find("img")
                    if img:
                        thumbnail = img.get("src", "")

                if not title_text:
                    continue

                items.append({
                    "external_id": f"xda_{hash(external_id) & 0xFFFFFFFF}",
                    "content_type": "post",
                    "title": title_text,
                    "body": body[:1000],
                    "url": url,
                    "thumbnail_url": thumbnail,
                    "published_at": published_at,
                })
            except Exception as e:
                self.logger.debug(f"Skipping XDA item: {e}")

        return items[:settings_limit()]


def settings_limit() -> int:
    from techpulse.config.settings import settings
    return settings.MAX_POSTS_PER_RUN
