from __future__ import annotations
"""Scrapes Amazon España bestseller and new-releases charts using Playwright.

Amazon renders products via JavaScript — simple HTTP scraping returns an empty grid.
Playwright renders the full page before parsing, like a real browser.
"""
import logging
from dataclasses import dataclass

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
    """Extract products from a fully-rendered Amazon bestsellers/new-releases page."""
    soup = BeautifulSoup(html, "html.parser")
    results: list[AmazonProduct] = []

    # After JS renders, products live in zg-grid-general-faceout divs
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
    """Shared Playwright fetch + parse logic for any Amazon zg/nr page."""
    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except ImportError:
        return [], "Playwright no instalado. Ejecuta: pip install playwright && playwright install chromium"

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                locale="es-ES",
                timezone_id="Europe/Madrid",
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0.0.0 Safari/537.36"
                ),
            )
            page = context.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=20_000)

            try:
                page.wait_for_selector(
                    "div.zg-grid-general-faceout, li.zg-item-immersion",
                    timeout=10_000,
                )
            except Exception:
                pass  # Parse whatever loaded

            html = page.content()
            browser.close()

        products = _parse_page(html, limit)
        if not products:
            return [], (
                "No se encontraron productos tras renderizar la página. "
                "Amazon puede haber actualizado su estructura."
            )
        return products, None

    except Exception as e:
        logger.warning(f"Amazon Playwright scrape failed ({context_label}): {e}")
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
