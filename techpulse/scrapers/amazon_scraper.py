from __future__ import annotations
"""Scrapes Amazon España bestseller and new-releases charts.

Uses httpx with realistic browser headers.  Amazon bestseller pages include
product data in the initial server-rendered HTML, so a headless browser is
*not* required.
"""
import logging
from dataclasses import dataclass

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# ── Más vendidos ───────────────────────────────────────────────────────────────
_BESTSELLERS_URLS: dict[str, str] = {
    "📱 Móviles":      "https://www.amazon.es/gp/bestsellers/electronics/17425698031/",
    "⌚ Smartwatches": "https://www.amazon.es/gp/bestsellers/electronics/3457446031/",
    "📲 Tablets":      "https://www.amazon.es/gp/bestsellers/computers/938010031/",
    "💻 Portátiles":   "https://www.amazon.es/gp/bestsellers/computers/938008031/",
    "🎮 Gaming":       "https://www.amazon.es/gp/bestsellers/videogames/",
}

# ── Novedades ──────────────────────────────────────────────────────────────────
_NEW_RELEASES_URLS: dict[str, str] = {
    "📱 Móviles":      "https://www.amazon.es/gp/new-releases/electronics/17425698031/",
    "⌚ Smartwatches": "https://www.amazon.es/gp/new-releases/electronics/3457446031/",
    "📲 Tablets":      "https://www.amazon.es/gp/new-releases/computers/938010031/",
    "💻 Portátiles":   "https://www.amazon.es/gp/new-releases/computers/938008031/",
    "🎮 Gaming":       "https://www.amazon.es/gp/new-releases/videogames/",
}

CATEGORY_LABELS = list(_BESTSELLERS_URLS.keys())

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Cache-Control": "no-cache",
}


@dataclass
class AmazonProduct:
    rank:   int
    title:  str
    price:  str
    rating: str
    url:    str


# Keep backwards-compatible alias
BestsellerProduct = AmazonProduct


def _parse_page(html: str, limit: int) -> list[AmazonProduct]:
    """Extract products from an Amazon bestsellers/new-releases page."""
    soup = BeautifulSoup(html, "html.parser")
    results: list[AmazonProduct] = []

    # Products live in zg-grid-general-faceout divs
    items = (
        soup.select("div.zg-grid-general-faceout")
        or soup.select("li.zg-item-immersion")
        or soup.select("div[id^='gridItemRoot']")
    )

    for idx, item in enumerate(items[:limit], start=1):
        # ── title ──────────────────────────────────────────────────────────
        title_el = (
            item.select_one("div.p13n-sc-truncate-desktop-type2")
            or item.select_one("div[class*='p13n-sc-css-line-clamp']")
            or item.select_one("span[class*='p13n-sc-css-line-clamp']")
            or item.select_one("a.a-link-normal span.a-text-normal")
            or item.select_one("span.zg-text-center-align a span")
        )
        title = title_el.get_text(strip=True) if title_el else ""
        if not title or len(title) < 4:
            continue

        # ── price ──────────────────────────────────────────────────────────
        price_el = (
            item.select_one("span.p13n-sc-price")
            or item.select_one("span[class*='p13n-sc-price']")
            or item.select_one("span.a-price span.a-offscreen")
        )
        price = price_el.get_text(strip=True) if price_el else "—"

        # ── rating ─────────────────────────────────────────────────────────
        rating_el = item.select_one("span.a-icon-alt")
        rating = ""
        if rating_el:
            parts = rating_el.get_text(strip=True).split()
            if parts:
                rating = f"{parts[0].replace(',', '.')}⭐"

        # ── url ────────────────────────────────────────────────────────────
        link_el = item.select_one("a.a-link-normal[href]")
        href = (link_el["href"] if link_el and link_el.get("href") else "").split("?")[0]
        full_url = f"https://www.amazon.es{href}" if href.startswith("/") else href

        # ── rank ───────────────────────────────────────────────────────────
        rank_el = item.select_one("span.zg-bdg-text") or item.select_one("span#zg-badge-text")
        try:
            rank = int(rank_el.get_text(strip=True).lstrip("#")) if rank_el else idx
        except (ValueError, AttributeError):
            rank = idx

        results.append(AmazonProduct(rank=rank, title=title, price=price, rating=rating, url=full_url))

    return sorted(results, key=lambda x: x.rank)


def _fetch_amazon(url: str, context_label: str, limit: int) -> tuple[list[AmazonProduct], str | None]:
    """Fetch an Amazon page via httpx and parse products."""
    try:
        resp = httpx.get(url, headers=_HEADERS, follow_redirects=True, timeout=20)
        resp.raise_for_status()
        html = resp.text

        products = _parse_page(html, limit)
        if not products:
            return [], (
                "No se encontraron productos. "
                "Amazon puede haber bloqueado la petición o cambiado su estructura."
            )
        return products, None

    except httpx.HTTPStatusError as e:
        logger.warning(f"Amazon HTTP error ({context_label}): {e.response.status_code}")
        return [], f"Amazon devolvió HTTP {e.response.status_code}"
    except Exception as e:
        logger.warning(f"Amazon scrape failed ({context_label}): {e}")
        return [], f"Error al cargar Amazon: {e}"


def get_bestsellers(category_label: str, limit: int = 20) -> tuple[list[AmazonProduct], str | None]:
    """Fetch Amazon ES bestsellers for the given category.

    Returns:
        (products, error_message) — error_message is None on success.
    """
    url = _BESTSELLERS_URLS.get(category_label)
    if not url:
        return [], f"Categoría '{category_label}' no configurada."
    return _fetch_amazon(url, f"bestsellers/{category_label}", limit)


def get_new_releases(category_label: str, limit: int = 20) -> tuple[list[AmazonProduct], str | None]:
    """Fetch Amazon ES new releases for the given category.

    Returns:
        (products, error_message) — error_message is None on success.
    """
    url = _NEW_RELEASES_URLS.get(category_label)
    if not url:
        return [], f"Categoría '{category_label}' no configurada."
    return _fetch_amazon(url, f"new-releases/{category_label}", limit)
