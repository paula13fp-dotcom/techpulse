from __future__ import annotations
"""Tech-blog scrapers via RSS feeds — noticias, leaks y rumores.

Fuentes en español
------------------
* Xataka          — https://www.xataka.com
* Xataka Móvil    — https://www.xatakamovil.com
* MuyComputer     — https://www.muycomputer.com
* Andro4all       — https://andro4all.com
* Hipertextual    — https://hipertextual.com
* Applesfera      — https://www.applesfera.com
* El Androide Libre — https://elandroidelibre.elespanol.com
* Omicrono        — https://omicrono.elespanol.com
* Hardzone        — https://hardzone.es
* ComputerHoy     — https://computerhoy.com

Fuentes en inglés — leaks y rumores
-------------------------------------
* 9to5Mac         — Apple leaks/exclusivas (https://9to5mac.com)
* 9to5Google      — Google/Android leaks (https://9to5google.com)
* MacRumors       — Rumores Apple, supply chain (https://macrumors.com)
* Android Authority — Android noticias y exclusivas (https://androidauthority.com)
* Wccftech        — GPU/PC leaks, Intel/AMD/NVIDIA (https://wccftech.com)
* The Verge       — Cobertura tech amplia de calidad (https://theverge.com)
* SamMobile       — Samsung leaks, firmware, rumores (https://sammobile.com)
* PhoneArena      — Noticias y rumores de móviles (https://phonearena.com)

All use RSS / Atom feeds so no HTML scraping is needed.
"""

from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup

from techpulse.config.constants import SCRAPE_DELAY_SECONDS
from techpulse.scrapers.base import BaseScraper
from techpulse.utils.rate_limiter import RateLimiter


# --------------------------------------------------------------------------- #
# Shared base for RSS-based blogs
# --------------------------------------------------------------------------- #

class _RSSBlogScraper(BaseScraper):
    """Base class for any source that exposes a standard RSS / Atom feed."""

    feed_url: str  # Override in subclass

    def __init__(self):
        super().__init__()
        self._limiter = RateLimiter(calls_per_second=1.0 / SCRAPE_DELAY_SECONDS)
        self._headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
            "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
        }

    def fetch(self) -> list[dict]:
        self._limiter.wait()
        try:
            with httpx.Client(
                headers=self._headers, timeout=20, follow_redirects=True
            ) as client:
                resp = client.get(self.feed_url)
                resp.raise_for_status()
            return self._parse_feed(resp.text)
        except Exception as e:
            self.logger.error(f"{self.source_name} feed fetch failed: {e}")
            return []

    def _parse_feed(self, xml: str) -> list[dict]:
        """Parse RSS 2.0 or Atom 1.0 feed and return normalised item dicts."""
        from techpulse.config.settings import settings

        soup = BeautifulSoup(xml, "xml")
        items: list[dict] = []

        # RSS 2.0 — <item> elements
        for node in soup.find_all("item"):
            item = self._parse_rss_item(node)
            if item:
                items.append(item)

        # Atom 1.0 — <entry> elements (fallback)
        if not items:
            for node in soup.find_all("entry"):
                item = self._parse_atom_entry(node)
                if item:
                    items.append(item)

        return items[: settings.MAX_POSTS_PER_RUN]

    # ── RSS 2.0 ──────────────────────────────────────────────────────────────

    def _parse_rss_item(self, node) -> dict | None:
        title_tag = node.find("title")
        link_tag = node.find("link")
        desc_tag = node.find("description")
        date_tag = node.find("pubDate")
        guid_tag = node.find("guid")

        title = title_tag.get_text(strip=True) if title_tag else ""
        if not title:
            return None

        url = link_tag.get_text(strip=True) if link_tag else ""
        if not url:
            # <link> can be an attribute-only tag in some parsers
            url = link_tag.get("href", "") if link_tag else ""

        body = ""
        thumb = ""
        if desc_tag:
            raw = desc_tag.get_text(strip=True)
            # strip embedded HTML markup that ends up in description
            desc_soup = BeautifulSoup(raw, "html.parser")
            img = desc_soup.find("img")
            if img:
                thumb = img.get("src", "")
            body = desc_soup.get_text(separator=" ", strip=True)[:1000]

        external_id = guid_tag.get_text(strip=True) if guid_tag else url
        published_at = self._parse_rss_date(date_tag.get_text(strip=True) if date_tag else "")

        return {
            "external_id": f"{self.source_name}_{hash(external_id) & 0xFFFFFFFF}",
            "content_type": "article",
            "title": title,
            "body": body,
            "url": url,
            "thumbnail_url": thumb,
            "published_at": published_at,
        }

    # ── Atom 1.0 ─────────────────────────────────────────────────────────────

    def _parse_atom_entry(self, node) -> dict | None:
        title_tag = node.find("title")
        link_tag = node.find("link")
        summary_tag = node.find("summary") or node.find("content")
        updated_tag = node.find("updated") or node.find("published")
        id_tag = node.find("id")

        title = title_tag.get_text(strip=True) if title_tag else ""
        if not title:
            return None

        url = link_tag.get("href", "") if link_tag else ""
        body = summary_tag.get_text(separator=" ", strip=True)[:1000] if summary_tag else ""
        external_id = id_tag.get_text(strip=True) if id_tag else url
        published_at = self._parse_iso_date(updated_tag.get_text(strip=True) if updated_tag else "")

        return {
            "external_id": f"{self.source_name}_{hash(external_id) & 0xFFFFFFFF}",
            "content_type": "article",
            "title": title,
            "body": body,
            "url": url,
            "thumbnail_url": "",
            "published_at": published_at,
        }

    # ── Date helpers ─────────────────────────────────────────────────────────

    @staticmethod
    def _parse_rss_date(date_str: str) -> str:
        """Parse RFC 2822 dates (common in RSS) to ISO 8601."""
        if not date_str:
            return datetime.now(timezone.utc).isoformat()
        try:
            from email.utils import parsedate_to_datetime
            return parsedate_to_datetime(date_str).isoformat()
        except Exception:
            return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _parse_iso_date(date_str: str) -> str:
        """Parse ISO 8601 dates (common in Atom) robustly."""
        if not date_str:
            return datetime.now(timezone.utc).isoformat()
        try:
            # Handle trailing Z
            return datetime.fromisoformat(date_str.replace("Z", "+00:00")).isoformat()
        except Exception:
            return datetime.now(timezone.utc).isoformat()


# --------------------------------------------------------------------------- #
# Concrete scrapers — one per blog
# --------------------------------------------------------------------------- #

class XatakaScraper(_RSSBlogScraper):
    """Xataka — principal blog de tecnología en España."""
    source_name = "xataka"
    feed_url = "https://feeds.weblogssl.com/xataka2"


class XatakaMovilScraper(_RSSBlogScraper):
    """Xataka Móvil — análisis y noticias de smartphones."""
    source_name = "xatakamovil"
    feed_url = "https://feeds.weblogssl.com/xatakamovil"


class MuyComputerScraper(_RSSBlogScraper):
    """MuyComputer — noticias de hardware y tecnología."""
    source_name = "muycomputer"
    feed_url = "https://www.muycomputer.com/feed/"


class Andro4allScraper(_RSSBlogScraper):
    """Andro4all — Android, móviles y tecnología."""
    source_name = "andro4all"
    feed_url = "https://andro4all.com/feed"


class HipertextualScraper(_RSSBlogScraper):
    """Hipertextual — ciencia, tecnología y cultura digital."""
    source_name = "hipertextual"
    feed_url = "https://hipertextual.com/feed"


class ApplesferaScraper(_RSSBlogScraper):
    """Applesfera — Apple, iPhone, iPad y Mac en español."""
    source_name = "applesfera"
    feed_url = "https://feeds.weblogssl.com/applesfera"


# --------------------------------------------------------------------------- #
# Blogs en español — adicionales
# --------------------------------------------------------------------------- #

class HardzoneScraper(_RSSBlogScraper):
    """Hardzone — hardware PC, componentes y periféricos."""
    source_name = "hardzone"
    feed_url = "https://hardzone.es/feed/"


class TuExpertoScraper(_RSSBlogScraper):
    """TuExperto — noticias tech, móviles y gadgets en español."""
    source_name = "tuexperto"
    feed_url = "https://www.tuexperto.com/feed/"


class IPhonerosScraper(_RSSBlogScraper):
    """iPhoneros — Apple, iPhone, iPad y Mac en español."""
    source_name = "iphoneros"
    feed_url = "https://iphoneros.com/feed"


# --------------------------------------------------------------------------- #
# Fuentes en inglés — leaks, rumores y noticias
# --------------------------------------------------------------------------- #

class NineToFiveMacScraper(_RSSBlogScraper):
    """9to5Mac — exclusivas y leaks de productos Apple no anunciados."""
    source_name = "9to5mac"
    feed_url = "https://9to5mac.com/feed/"


class NineToFiveGoogleScraper(_RSSBlogScraper):
    """9to5Google — leaks y exclusivas de Google, Android y Pixel."""
    source_name = "9to5google"
    feed_url = "https://9to5google.com/feed/"


class MacRumorsScraper(_RSSBlogScraper):
    """MacRumors — rumores Apple basados en supply chain y filtraciones."""
    source_name = "macrumors"
    feed_url = "https://feeds.macrumors.com/MacRumors-All"


class AndroidAuthorityScraper(_RSSBlogScraper):
    """Android Authority — noticias Android, exclusivas y análisis."""
    source_name = "androidauthority"
    feed_url = "https://www.androidauthority.com/feed/"


class WccftechScraper(_RSSBlogScraper):
    """Wccftech — leaks de GPU, CPU y hardware PC (NVIDIA, AMD, Intel)."""
    source_name = "wccftech"
    feed_url = "https://wccftech.com/feed/"


class TheVergeScraper(_RSSBlogScraper):
    """The Verge — cobertura tech de referencia, reviews y noticias."""
    source_name = "theverge"
    feed_url = "https://www.theverge.com/rss/index.xml"


class SamMobileScraper(_RSSBlogScraper):
    """SamMobile — leaks Samsung, firmware, Galaxy no anunciados."""
    source_name = "sammobile"
    feed_url = "https://www.sammobile.com/feed/"


class AndroidPoliceScraper(_RSSBlogScraper):
    """Android Police — leaks Android, Google Pixel y exclusivas."""
    source_name = "androidpolice"
    feed_url = "https://www.androidpolice.com/feed/"


class PhandroidScraper(_RSSBlogScraper):
    """Phandroid — noticias Android, comparativas y rumores."""
    source_name = "phandroid"
    feed_url = "https://phandroid.com/feed/"


class TechRadarScraper(_RSSBlogScraper):
    """TechRadar — cobertura tech global, reviews y noticias de lanzamientos."""
    source_name = "techradar"
    feed_url = "https://www.techradar.com/rss"
