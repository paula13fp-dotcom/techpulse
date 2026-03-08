from __future__ import annotations
"""PCComponents product search via Algolia API.

PCComponents uses Algolia as their search backend. The public search-only
API key and App ID are embedded in their frontend and are intended for
client use. This scraper calls the same API the browser uses.
"""
from dataclasses import dataclass, field

import httpx

from techpulse.utils.rate_limiter import RateLimiter
from techpulse.utils.logger import get_logger

logger = get_logger("scraper.pccomponents")

_ALGOLIA_APP_ID = "BEWOYX1CF1"
_ALGOLIA_API_KEY = "47978d8b445ceaceb718dd842d434099"
_INDEX = "products_list:es"
_SEARCH_URL = f"https://{_ALGOLIA_APP_ID}-dsn.algolia.net/1/indexes/{_INDEX}/query"
_PRODUCT_BASE_URL = "https://www.pccomponentes.com/"

_HEADERS = {
    "X-Algolia-Application-Id": _ALGOLIA_APP_ID,
    "X-Algolia-API-Key": _ALGOLIA_API_KEY,
    "Content-Type": "application/json",
}

_limiter = RateLimiter(calls_per_second=0.5)


@dataclass
class PCProduct:
    name: str
    price: str
    url: str
    available: bool
    image_url: str = ""
    rating: str = ""
    stock: int = 0
    discount: float = 0.0
    stock_label: str = ""


@dataclass
class PCSearchResult:
    query: str
    found: bool
    total_hits: int = 0
    products: list[PCProduct] = field(default_factory=list)
    error: str = ""


def search_product(product_name: str) -> PCSearchResult:
    """Search for a product on PCComponents via Algolia and return results."""
    _limiter.wait()

    try:
        body = {
            "query": product_name,
            "hitsPerPage": 8,
            "attributesToRetrieve": [
                "name", "price", "promotionalPrice", "slug",
                "stock", "availability", "ratingAvg", "ratingCount",
                "discount", "images", "brandName",
            ],
        }

        with httpx.Client(timeout=15) as client:
            resp = client.post(_SEARCH_URL, headers=_HEADERS, json=body)
            resp.raise_for_status()

        data = resp.json()
        hits = data.get("hits", [])
        total = data.get("nbHits", 0)

        products = [p for p in (_normalize_hit(h) for h in hits) if p is not None]

        return PCSearchResult(
            query=product_name,
            found=len(products) > 0,
            total_hits=total,
            products=products,
        )

    except httpx.HTTPStatusError as e:
        logger.warning(f"PCComponents HTTP {e.response.status_code} for '{product_name}'")
        return PCSearchResult(query=product_name, found=False, error=f"HTTP {e.response.status_code}")
    except Exception as e:
        logger.error(f"PCComponents search failed for '{product_name}': {e}")
        return PCSearchResult(query=product_name, found=False, error=str(e))


def _normalize_hit(hit: dict) -> PCProduct | None:
    name = hit.get("name", "")
    if not name:
        return None

    slug = hit.get("slug", "")
    url = f"{_PRODUCT_BASE_URL}{slug}" if slug else ""

    promo = hit.get("promotionalPrice")
    regular = hit.get("price", 0)
    price_val = promo if promo else regular
    price_str = f"{price_val:.2f} €" if price_val else "Precio no disponible"

    stock = hit.get("stock") or 0
    # availability is a list like ['MURCIA', 'MADRID', 'IN_STOCK'] or ['OUT_OF_STOCK'] or []
    availability_raw = hit.get("availability") or []
    if isinstance(availability_raw, list) and availability_raw:
        available = "OUT_OF_STOCK" not in availability_raw
    else:
        # No availability data — fall back to stock count
        available = stock > 0

    images = hit.get("images", {})
    # images is a dict: {"small": {"path": "..."}, "medium": {...}}
    image_url = ""
    if isinstance(images, dict):
        img_data = images.get("medium") or images.get("small") or {}
        image_url = img_data.get("path", "") if isinstance(img_data, dict) else ""
    elif isinstance(images, list) and images:
        image_url = str(images[0])

    rating_avg = hit.get("ratingAvg", 0)
    rating_count = hit.get("ratingCount", 0)
    rating = f"★ {rating_avg:.1f} ({rating_count})" if rating_avg else ""

    # Build human-readable stock label from availability list
    store_names = {"MURCIA", "MADRID", "BARCELONA", "THADER", "VALENCIA", "SEVILLA", "BILBAO"}
    if isinstance(availability_raw, list) and availability_raw:
        stores = [s.capitalize() for s in availability_raw if s in store_names]
        if "IN_STOCK" in availability_raw and stores:
            stock_label = f"En stock · {', '.join(stores)}"
        elif "IN_STOCK" in availability_raw:
            stock_label = "En stock"
        elif stores:
            stock_label = f"En tienda: {', '.join(stores)}"
        else:
            stock_label = "Sin stock"
    else:
        stock_label = "En stock" if stock > 0 else "Sin stock"

    return PCProduct(
        name=name,
        price=price_str,
        url=url,
        available=available,
        image_url=image_url,
        rating=rating,
        stock=int(stock),
        discount=float(hit.get("discount", 0) or 0),
        stock_label=stock_label,
    )


def batch_search(product_names: list[str]) -> list[PCSearchResult]:
    """Search multiple products with rate limiting."""
    results = []
    for name in product_names:
        result = search_product(name)
        results.append(result)
        logger.info(f"PCComponents: '{name}' → {result.total_hits} hits")
    return results
