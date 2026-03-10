from __future__ import annotations
"""Load and validate configuration from .env file."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
_env_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(_env_path, override=True)


def _get(key: str, default: str | None = None, required: bool = False) -> str | None:
    value = os.environ.get(key, default)
    if required and not value:
        raise ValueError(f"Missing required environment variable: {key}")
    return value


class Settings:
    # Reddit
    REDDIT_CLIENT_ID: str | None = _get("REDDIT_CLIENT_ID")
    REDDIT_CLIENT_SECRET: str | None = _get("REDDIT_CLIENT_SECRET")
    REDDIT_USER_AGENT: str = _get("REDDIT_USER_AGENT", "TechPulse/1.0 by user")

    # YouTube
    YOUTUBE_API_KEY: str | None = _get("YOUTUBE_API_KEY")

    # Anthropic
    ANTHROPIC_API_KEY: str | None = _get("ANTHROPIC_API_KEY")

    # X / Twitter (twikit)
    X_USERNAME: str | None = _get("X_USERNAME")
    X_EMAIL: str | None = _get("X_EMAIL")
    X_PASSWORD: str | None = _get("X_PASSWORD")

    # Scraping
    SCRAPE_INTERVAL_HOURS: int = int(_get("SCRAPE_INTERVAL_HOURS", "6"))
    MAX_POSTS_PER_RUN: int = int(_get("MAX_POSTS_PER_RUN", "100"))

    # Paths
    PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]
    DB_PATH: Path = PROJECT_ROOT / "techpulse.db"
    LOG_PATH: Path = PROJECT_ROOT / "logs" / "techpulse.log"

    @classmethod
    def has_reddit(cls) -> bool:
        return bool(cls.REDDIT_CLIENT_ID and cls.REDDIT_CLIENT_SECRET)

    @classmethod
    def has_youtube(cls) -> bool:
        return bool(cls.YOUTUBE_API_KEY)

    @classmethod
    def has_anthropic(cls) -> bool:
        return bool(cls.ANTHROPIC_API_KEY)

    @classmethod
    def has_x(cls) -> bool:
        return bool(cls.X_USERNAME and cls.X_EMAIL and cls.X_PASSWORD)

    @classmethod
    def configured_sources(cls) -> list[str]:
        sources = []
        if cls.has_reddit():
            sources.append("reddit")
        if cls.has_youtube():
            sources.append("youtube")
        # Forum scrapers need no API key
        sources.extend(["xda", "gsmarena"])
        # TikTok always attempted (may fail gracefully)
        sources.append("tiktok")
        # X / Twitter (twikit)
        if cls.has_x():
            sources.append("x")
        return sources


settings = Settings()
