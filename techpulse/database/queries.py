from __future__ import annotations
"""Reusable database query functions."""
from typing import Any
from sqlalchemy import text

from techpulse.database.connection import get_db


def get_feed(
    source_name: str | None = None,
    category_slug: str | None = None,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    """Return posts for the feed, optionally filtered by source, category or free-text search."""
    with get_db() as conn:
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        where_clauses = []

        if source_name:
            where_clauses.append("s.name = :source_name")
            params["source_name"] = source_name

        if category_slug:
            where_clauses.append("""
                EXISTS (
                    SELECT 1 FROM post_categories pc
                    JOIN device_categories dc ON pc.category_id = dc.id
                    WHERE pc.post_id = p.id AND dc.slug = :category_slug
                )
            """)
            params["category_slug"] = category_slug

        if search:
            where_clauses.append("(p.title LIKE :search OR p.body LIKE :search)")
            params["search"] = f"%{search}%"

        where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

        rows = conn.execute(text(f"""
            SELECT p.id, p.title, p.body, p.url, p.author,
                   p.score, p.comment_count, p.view_count, p.published_at,
                   s.name AS source_name, s.display_name AS source_display,
                   sr.label AS sentiment, sr.positive_score, sr.negative_score
            FROM posts p
            JOIN sources s ON p.source_id = s.id
            LEFT JOIN sentiment_results sr ON sr.post_id = p.id
            {where_sql}
            ORDER BY p.published_at DESC
            LIMIT :limit OFFSET :offset
        """), params).fetchall()
        return [dict(r._mapping) for r in rows]


def get_trending_topics(limit: int = 10) -> list[dict]:
    """Return top trending topic clusters."""
    with get_db() as conn:
        rows = conn.execute(text("""
            SELECT tc.id, tc.label, tc.description, tc.post_count,
                   tc.is_trending, tc.last_seen_at,
                   dc.name AS category_name,
                   pr.canonical_name AS product_name
            FROM topic_clusters tc
            LEFT JOIN device_categories dc ON tc.category_id = dc.id
            LEFT JOIN products pr ON tc.product_id = pr.id
            ORDER BY tc.is_trending DESC, tc.post_count DESC, tc.last_seen_at DESC
            LIMIT :limit
        """), {"limit": limit}).fetchall()
        return [dict(r._mapping) for r in rows]


def get_product_sentiment(category_slug: str | None = None) -> list[dict]:
    """Return per-product sentiment aggregates."""
    with get_db() as conn:
        cat_filter = ""
        params: dict[str, Any] = {}
        if category_slug:
            cat_filter = "AND dc.slug = :slug"
            params["slug"] = category_slug

        rows = conn.execute(text(f"""
            SELECT pr.id, pr.canonical_name, pr.brand, dc.name AS category,
                   COUNT(sr.id) AS total_posts,
                   ROUND(AVG(sr.positive_score) * 100, 1) AS avg_positive,
                   ROUND(AVG(sr.neutral_score) * 100, 1) AS avg_neutral,
                   ROUND(AVG(sr.negative_score) * 100, 1) AS avg_negative
            FROM products pr
            JOIN device_categories dc ON pr.category_id = dc.id
            JOIN post_product_mentions ppm ON ppm.product_id = pr.id
            JOIN sentiment_results sr ON sr.post_id = ppm.post_id
            WHERE pr.is_tracked = 1
            {cat_filter}
            GROUP BY pr.id
            HAVING total_posts >= 3
            ORDER BY total_posts DESC
        """), params).fetchall()
        return [dict(r._mapping) for r in rows]


def get_latest_digest(digest_type: str = "daily") -> dict | None:
    """Return the most recent digest of the given type."""
    with get_db() as conn:
        row = conn.execute(text("""
            SELECT id, digest_type, period_start, period_end, content, generated_at
            FROM digests
            WHERE digest_type = :dtype
            ORDER BY generated_at DESC
            LIMIT 1
        """), {"dtype": digest_type}).fetchone()
        return dict(row._mapping) if row else None


def get_unanalyzed_posts(limit: int = 50) -> list[dict]:
    """Return posts that don't yet have sentiment analysis."""
    with get_db() as conn:
        rows = conn.execute(text("""
            SELECT p.id, p.title, p.body, p.source_id
            FROM posts p
            LEFT JOIN sentiment_results sr ON sr.post_id = p.id
            WHERE sr.id IS NULL
              AND (p.body IS NOT NULL OR p.title IS NOT NULL)
            ORDER BY p.scraped_at DESC
            LIMIT :limit
        """), {"limit": limit}).fetchall()
        return [dict(r._mapping) for r in rows]


def get_post_count() -> int:
    with get_db() as conn:
        row = conn.execute(text("SELECT COUNT(*) as n FROM posts")).fetchone()
        return row.n if row else 0


def get_source_stats() -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(text("""
            SELECT s.display_name, COUNT(p.id) AS post_count,
                   MAX(p.scraped_at) AS last_scraped
            FROM sources s
            LEFT JOIN posts p ON p.source_id = s.id
            GROUP BY s.id
            ORDER BY post_count DESC
        """)).fetchall()
        return [dict(r._mapping) for r in rows]
