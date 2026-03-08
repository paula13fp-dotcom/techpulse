"""Assign device categories to posts based on keyword matching."""
from techpulse.config.constants import PRODUCT_KEYWORDS

_PHONE_KEYWORDS = {
    "phone", "smartphone", "iphone", "android", "samsung", "pixel", "oneplus",
    "xiaomi", "galaxy s", "nothing phone", "motorola", "huawei", "oppo", "vivo",
    "realme", "poco", "rog phone", "fold", "flip",
}
_WATCH_KEYWORDS = {
    "smartwatch", "watch", "wearable", "wear os", "apple watch", "galaxy watch",
    "pixel watch", "fitbit", "garmin",
}
_TABLET_KEYWORDS = {
    "tablet", "ipad", "galaxy tab", "matebook", "pixel tablet", "surface",
    "lenovo tab", "android tablet",
}


def tag_categories(title: str, body: str) -> list[str]:
    """Return list of matching category slugs for the given text."""
    text = f"{title or ''} {body or ''}".lower()
    categories = []
    if any(kw in text for kw in _PHONE_KEYWORDS):
        categories.append("phones")
    if any(kw in text for kw in _WATCH_KEYWORDS):
        categories.append("smartwatches")
    if any(kw in text for kw in _TABLET_KEYWORDS):
        categories.append("tablets")
    return categories or ["phones"]  # Default to phones if nothing matches


def find_product_mentions(title: str, body: str) -> list[str]:
    """Return list of canonical product names mentioned in the text."""
    text = f"{title or ''} {body or ''}".lower()
    found = []
    for keyword, canonical in PRODUCT_KEYWORDS.items():
        if keyword in text:
            found.append(canonical)
    return list(dict.fromkeys(found))  # Deduplicate preserving order
