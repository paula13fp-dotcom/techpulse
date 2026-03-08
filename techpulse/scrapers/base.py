from __future__ import annotations
"""Abstract base class for all scrapers."""
import hashlib
from abc import ABC, abstractmethod
from datetime import datetime, timezone

from sqlalchemy import text

from techpulse.database.connection import get_db
from techpulse.utils.logger import get_logger
from techpulse.utils.category_tagger import tag_categories, find_product_mentions
from techpulse.utils.text_cleaner import clean_text


class BaseScraper(ABC):
    source_name: str  # Override in subclasses

    def __init__(self):
        self.logger = get_logger(f"scraper.{self.source_name}")

    @abstractmethod
    def fetch(self) -> list[dict]:
        """Fetch raw items from the source. Return list of normalized dicts."""

    def run(self) -> int:
        """Fetch, store, and tag posts. Returns number of new posts saved."""
        self.logger.info(f"Starting scrape for {self.source_name}")
        try:
            items = self.fetch()
        except Exception as e:
            self.logger.error(f"Fetch failed: {e}")
            return 0

        saved = 0
        with get_db() as conn:
            source_id = self._get_source_id(conn)
            for item in items:
                try:
                    post_id = self._save_post(conn, source_id, item)
                    if post_id:
                        self._tag_post(conn, post_id, item)
                        saved += 1
                    conn.commit()
                except Exception as e:
                    self.logger.warning(f"Failed to save post {item.get('external_id')}: {e}")

        self.logger.info(f"Saved {saved} new posts from {self.source_name}")
        return saved

    def _get_source_id(self, conn) -> int:
        row = conn.execute(
            text("SELECT id FROM sources WHERE name = :name"),
            {"name": self.source_name}
        ).fetchone()
        if not row:
            raise RuntimeError(f"Source '{self.source_name}' not found in DB")
        return row.id

    def _save_post(self, conn, source_id: int, item: dict) -> int | None:
        content_hash = hashlib.sha256(
            f"{source_id}:{item['external_id']}".encode()
        ).hexdigest()

        # Check duplicate
        existing = conn.execute(
            text("SELECT id FROM posts WHERE content_hash = :h"),
            {"h": content_hash}
        ).fetchone()
        if existing:
            return None

        body_clean = clean_text(item.get("body", "") or "")
        title_clean = clean_text(item.get("title", "") or "")

        result = conn.execute(text("""
            INSERT OR IGNORE INTO posts
            (source_id, external_id, content_type, title, body, body_raw,
             author, url, thumbnail_url, upvotes, score, comment_count,
             view_count, like_count, share_count, published_at, content_hash)
            VALUES
            (:source_id, :external_id, :content_type, :title, :body, :body_raw,
             :author, :url, :thumbnail_url, :upvotes, :score, :comment_count,
             :view_count, :like_count, :share_count, :published_at, :content_hash)
        """), {
            "source_id": source_id,
            "external_id": item["external_id"],
            "content_type": item.get("content_type", "post"),
            "title": title_clean,
            "body": body_clean,
            "body_raw": item.get("body", ""),
            "author": item.get("author", ""),
            "url": item.get("url", ""),
            "thumbnail_url": item.get("thumbnail_url", ""),
            "upvotes": item.get("upvotes", 0),
            "score": item.get("score", 0),
            "comment_count": item.get("comment_count", 0),
            "view_count": item.get("view_count", 0),
            "like_count": item.get("like_count", 0),
            "share_count": item.get("share_count", 0),
            "published_at": item.get("published_at", datetime.now(timezone.utc).isoformat()),
            "content_hash": content_hash,
        })
        return result.lastrowid if result.rowcount else None

    def _tag_post(self, conn, post_id: int, item: dict):
        title = item.get("title", "")
        body = item.get("body", "")

        # Category tagging
        categories = tag_categories(title, body)
        for slug in categories:
            cat_row = conn.execute(
                text("SELECT id FROM device_categories WHERE slug = :slug"),
                {"slug": slug}
            ).fetchone()
            if cat_row:
                conn.execute(text("""
                    INSERT OR IGNORE INTO post_categories (post_id, category_id)
                    VALUES (:post_id, :cat_id)
                """), {"post_id": post_id, "cat_id": cat_row.id})

        # Product mention extraction
        product_names = find_product_mentions(title, body)
        for canonical_name in product_names:
            prod_row = conn.execute(
                text("SELECT id FROM products WHERE canonical_name = :name"),
                {"name": canonical_name}
            ).fetchone()
            if prod_row:
                conn.execute(text("""
                    INSERT OR IGNORE INTO post_product_mentions
                    (post_id, product_id, extracted_by)
                    VALUES (:post_id, :prod_id, 'regex')
                """), {"post_id": post_id, "prod_id": prod_row.id})
