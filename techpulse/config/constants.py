"""App-wide constants: categories, tracked subreddits, hashtags, keywords."""

DEVICE_CATEGORIES = {
    "phones": "Móviles",
    "smartwatches": "Smartwatches",
    "tablets": "Tablets",
}

# Reddit subreddits to monitor per category
SUBREDDITS = {
    "phones": [
        "Android", "iphone", "samsung", "GooglePixel",
        "OnePlus", "Xiaomi", "smartphones", "mobile",
        # Leaks y rumores
        "apple", "SamsungGalaxy", "hardware", "gadgets",
        "phonecomparisons", "NothingTech",
    ],
    "smartwatches": [
        "androidwear", "AppleWatch", "GalaxyWatch",
        "WearOS", "smartwatch",
        "wearables", "Garmin",
    ],
    "tablets": [
        "tablets", "ipad", "AndroidTablets", "GalaxyTab",
        "iPadPro",
    ],
}

# YouTube search queries per category
YOUTUBE_QUERIES = {
    "phones": [
        "best android phone 2026", "iphone 17 leaks", "samsung galaxy s26 rumores",
        "iphone 16 review", "samsung galaxy s25 review",
        "pixel 9 review", "xiaomi 15 review", "best smartphone 2026",
        "upcoming phones 2026", "phone leaks 2026",
    ],
    "smartwatches": [
        "best smartwatch 2026", "apple watch series 11 leaks",
        "apple watch ultra 2 review", "galaxy watch 8 rumores",
        "galaxy watch 7 review", "pixel watch review", "wear os 2026",
        "samsung galaxy ring review",
    ],
    "tablets": [
        "best tablet 2026", "ipad pro m5 leaks", "ipad air m3 rumores",
        "ipad pro review", "samsung galaxy tab s10 review",
        "android tablet review 2026", "galaxy tab s11 leaks",
    ],
}

# TikTok hashtags per category
TIKTOK_HASHTAGS = {
    "phones": [
        "smartphones", "androidreview", "iphonereview", "samsunggalaxy",
        "techreview", "newphone", "phoneunboxing",
    ],
    "smartwatches": [
        "smartwatch", "applewatch", "galaxywatch", "wearable",
    ],
    "tablets": [
        "tablet", "ipadreview", "androidtablet", "tabletreview",
    ],
}

# XDA forums URL patterns to scrape
XDA_FORUMS = {
    "phones": "https://xdadevelopers.com/forums/android.2/",
    "tablets": "https://xdadevelopers.com/forums/android.2/",
}

# GSMArena news URL
GSMARENA_NEWS_URL = "https://www.gsmarena.com/news.php3"

# Product keyword → canonical name mapping (seed list)
PRODUCT_KEYWORDS: dict[str, str] = {
    # ── Phones — lanzados ────────────────────────────────────────────────────
    "iphone 16": "Apple iPhone 16",
    "iphone 16 pro": "Apple iPhone 16 Pro",
    "iphone 16e": "Apple iPhone 16e",
    "iphone 15": "Apple iPhone 15",
    "galaxy s25": "Samsung Galaxy S25",
    "galaxy s25 ultra": "Samsung Galaxy S25 Ultra",
    "galaxy s25+": "Samsung Galaxy S25+",
    "galaxy s24": "Samsung Galaxy S24",
    "galaxy z fold 6": "Samsung Galaxy Z Fold 6",
    "galaxy z flip 6": "Samsung Galaxy Z Flip 6",
    "pixel 9": "Google Pixel 9",
    "pixel 9 pro": "Google Pixel 9 Pro",
    "pixel 8": "Google Pixel 8",
    "oneplus 13": "OnePlus 13",
    "xiaomi 15": "Xiaomi 15",
    "xiaomi 15 ultra": "Xiaomi 15 Ultra",
    "xiaomi 14": "Xiaomi 14",
    "nothing phone 3": "Nothing Phone 3",
    "nothing phone 2": "Nothing Phone 2",
    "huawei pura 70": "Huawei Pura 70",
    "motorola edge 50": "Motorola Edge 50",
    # ── Phones — próxima generación / rumores ─────────────────────────────────
    "iphone 17": "Apple iPhone 17",
    "iphone 17 pro": "Apple iPhone 17 Pro",
    "iphone 17 air": "Apple iPhone 17 Air",
    "iphone 17 pro max": "Apple iPhone 17 Pro Max",
    "galaxy s26": "Samsung Galaxy S26",
    "galaxy s26 ultra": "Samsung Galaxy S26 Ultra",
    "galaxy s26+": "Samsung Galaxy S26+",
    "galaxy z fold 7": "Samsung Galaxy Z Fold 7",
    "galaxy z flip 7": "Samsung Galaxy Z Flip 7",
    "pixel 10": "Google Pixel 10",
    "pixel 10 pro": "Google Pixel 10 Pro",
    "pixel 10a": "Google Pixel 10a",
    "pixel 9a": "Google Pixel 9a",
    "oneplus 14": "OnePlus 14",
    "xiaomi 16": "Xiaomi 16",
    "nothing phone 3a": "Nothing Phone 3a",
    # ── Otros / emergentes ───────────────────────────────────────────────────
    "unihertz atom": "Unihertz Atom",
    "atom phone": "Unihertz Atom",
    "atom xl": "Unihertz Atom XL",
    "atom l": "Unihertz Atom L",
    "iqoo 13": "iQOO 13",
    "iqoo 12": "iQOO 12",
    "poco x7": "Xiaomi POCO X7",
    "poco f7": "Xiaomi POCO F7",
    "redmi note 14": "Xiaomi Redmi Note 14",
    "redmi note 13": "Xiaomi Redmi Note 13",
    # ── Watches — lanzados ───────────────────────────────────────────────────
    "apple watch ultra 2": "Apple Watch Ultra 2",
    "apple watch ultra": "Apple Watch Ultra 2",
    "apple watch series 10": "Apple Watch Series 10",
    "galaxy watch 7": "Samsung Galaxy Watch 7",
    "galaxy watch ultra": "Samsung Galaxy Watch Ultra",
    "galaxy ring": "Samsung Galaxy Ring",
    "pixel watch 3": "Google Pixel Watch 3",
    "pixel watch": "Google Pixel Watch 3",
    "xiaomi watch s4": "Xiaomi Watch S4",
    "xiaomi watch s3": "Xiaomi Watch S3",
    "xiaomi watch 5": "Xiaomi Watch 5",
    "garmin fenix 8": "Garmin Fenix 8",
    "garmin fenix 7": "Garmin Fenix 7",
    # ── Watches — próxima generación / rumores ───────────────────────────────
    "apple watch series 11": "Apple Watch Series 11",
    "apple watch ultra 3": "Apple Watch Ultra 3",
    "galaxy watch 8": "Samsung Galaxy Watch 8",
    "pixel watch 4": "Google Pixel Watch 4",
    # ── Tablets — lanzados ───────────────────────────────────────────────────
    "ipad pro m4": "Apple iPad Pro M4",
    "ipad pro": "Apple iPad Pro",
    "ipad air m2": "Apple iPad Air M2",
    "ipad air": "Apple iPad Air",
    "ipad mini": "Apple iPad Mini",
    "galaxy tab s10": "Samsung Galaxy Tab S10",
    "galaxy tab s10+": "Samsung Galaxy Tab S10+",
    "galaxy tab s10 ultra": "Samsung Galaxy Tab S10 Ultra",
    "galaxy tab s9": "Samsung Galaxy Tab S9",
    "pixel tablet": "Google Pixel Tablet",
    "xiaomi pad 7": "Xiaomi Pad 7",
    "xiaomi pad 6": "Xiaomi Pad 6",
    # ── Tablets — próxima generación / rumores ───────────────────────────────
    "ipad pro m5": "Apple iPad Pro M5",
    "ipad air m3": "Apple iPad Air M3",
    "galaxy tab s11": "Samsung Galaxy Tab S11",
}

# X / Twitter search queries per category
X_QUERIES = {
    "phones": [
        "iPhone 17 leak", "iPhone 17 Pro", "iPhone 17 Air",
        "Samsung Galaxy S26", "Galaxy S26 Ultra",
        "Pixel 10", "Pixel 10 Pro",
        "best smartphone 2026", "upcoming phones 2026",
        "OnePlus 14", "Xiaomi 16",
    ],
    "smartwatches": [
        "Apple Watch Series 11", "Apple Watch Ultra 3",
        "Galaxy Watch 8", "Pixel Watch 4",
        "best smartwatch 2026",
    ],
    "tablets": [
        "iPad Pro M5", "iPad Air M3",
        "Galaxy Tab S11", "best tablet 2026",
    ],
}

# X / Twitter accounts to monitor (tech leakers & reviewers)
X_ACCOUNTS = [
    "markgurman", "UniverseIce", "evleaks", "OnLeaks",
    "MishaalRahman", "SnoopyTech_", "rabornes",
    "MajinBuOfficial", "FrontTron", "ZacksJerryRig",
]

# Rate limits
REDDIT_REQUESTS_PER_MINUTE = 60
YOUTUBE_DAILY_QUOTA = 10_000
X_SEARCHES_PER_RUN = 40
SCRAPE_DELAY_SECONDS = 2.0  # Between requests to polite-scrape forums
