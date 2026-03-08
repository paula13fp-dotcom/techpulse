"""SQLAlchemy Core table definitions."""
from sqlalchemy import (
    MetaData, Table, Column, Integer, Text, Float as Real, UniqueConstraint,
    ForeignKey, Index, text,
)

metadata = MetaData()

sources = Table(
    "sources", metadata,
    Column("id", Integer, primary_key=True),
    Column("name", Text, nullable=False, unique=True),
    Column("display_name", Text, nullable=False),
    Column("base_url", Text),
    Column("is_active", Integer, nullable=False, server_default=text("1")),
)

device_categories = Table(
    "device_categories", metadata,
    Column("id", Integer, primary_key=True),
    Column("slug", Text, nullable=False, unique=True),
    Column("name", Text, nullable=False),
)

products = Table(
    "products", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("canonical_name", Text, nullable=False, unique=True),
    Column("brand", Text),
    Column("model_family", Text),
    Column("category_id", Integer, ForeignKey("device_categories.id"), nullable=False),
    Column("aliases", Text),  # JSON array
    Column("release_date", Text),
    Column("is_tracked", Integer, nullable=False, server_default=text("1")),
    Column("created_at", Text, nullable=False, server_default=text("(datetime('now'))")),
    Index("idx_products_category", "category_id"),
    Index("idx_products_brand", "brand"),
)

posts = Table(
    "posts", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("source_id", Integer, ForeignKey("sources.id"), nullable=False),
    Column("external_id", Text, nullable=False),
    Column("content_type", Text, nullable=False),  # post, comment, video, short, thread_reply
    Column("title", Text),
    Column("body", Text),
    Column("body_raw", Text),
    Column("author", Text),
    Column("url", Text),
    Column("thumbnail_url", Text),
    Column("upvotes", Integer, server_default=text("0")),
    Column("downvotes", Integer, server_default=text("0")),
    Column("score", Integer, server_default=text("0")),
    Column("comment_count", Integer, server_default=text("0")),
    Column("view_count", Integer, server_default=text("0")),
    Column("like_count", Integer, server_default=text("0")),
    Column("share_count", Integer, server_default=text("0")),
    Column("published_at", Text, nullable=False),
    Column("scraped_at", Text, nullable=False, server_default=text("(datetime('now'))")),
    Column("updated_at", Text),
    Column("content_hash", Text),
    UniqueConstraint("source_id", "external_id", name="uq_posts_source_external"),
    Index("idx_posts_source", "source_id"),
    Index("idx_posts_published", "published_at"),
    Index("idx_posts_scraped", "scraped_at"),
    Index("idx_posts_content_type", "content_type"),
    Index("idx_posts_hash", "content_hash"),
)

post_product_mentions = Table(
    "post_product_mentions", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("post_id", Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False),
    Column("product_id", Integer, ForeignKey("products.id"), nullable=False),
    Column("mention_count", Integer, nullable=False, server_default=text("1")),
    Column("is_primary", Integer, nullable=False, server_default=text("0")),
    Column("extracted_by", Text, nullable=False, server_default=text("'regex'")),
    UniqueConstraint("post_id", "product_id", name="uq_mention_post_product"),
    Index("idx_mentions_post", "post_id"),
    Index("idx_mentions_product", "product_id"),
)

post_categories = Table(
    "post_categories", metadata,
    Column("post_id", Integer, ForeignKey("posts.id", ondelete="CASCADE"), primary_key=True),
    Column("category_id", Integer, ForeignKey("device_categories.id"), primary_key=True),
)

sentiment_results = Table(
    "sentiment_results", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("post_id", Integer, ForeignKey("posts.id", ondelete="CASCADE"), unique=True),
    Column("positive_score", Real, nullable=False, server_default=text("0.0")),
    Column("neutral_score", Real, nullable=False, server_default=text("0.0")),
    Column("negative_score", Real, nullable=False, server_default=text("0.0")),
    Column("label", Text, nullable=False),  # positive, neutral, negative, mixed
    Column("confidence", Real),
    Column("product_id", Integer, ForeignKey("products.id")),
    Column("model_used", Text, nullable=False, server_default=text("'claude-sonnet-4-6'")),
    Column("analyzed_at", Text, nullable=False, server_default=text("(datetime('now'))")),
    Column("batch_id", Text),
    Index("idx_sentiment_post", "post_id"),
    Index("idx_sentiment_product", "product_id"),
    Index("idx_sentiment_label", "label"),
    Index("idx_sentiment_analyzed", "analyzed_at"),
)

topic_clusters = Table(
    "topic_clusters", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("label", Text, nullable=False),
    Column("description", Text),
    Column("post_count", Integer, server_default=text("0")),
    Column("category_id", Integer, ForeignKey("device_categories.id")),
    Column("product_id", Integer, ForeignKey("products.id")),
    Column("first_seen_at", Text, nullable=False),
    Column("last_seen_at", Text, nullable=False),
    Column("is_trending", Integer, server_default=text("0")),
    Column("batch_id", Text),
)

cluster_posts = Table(
    "cluster_posts", metadata,
    Column("cluster_id", Integer, ForeignKey("topic_clusters.id", ondelete="CASCADE"), primary_key=True),
    Column("post_id", Integer, ForeignKey("posts.id", ondelete="CASCADE"), primary_key=True),
    Column("relevance", Real, server_default=text("1.0")),
)

digests = Table(
    "digests", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("digest_type", Text, nullable=False),  # daily, weekly
    Column("period_start", Text, nullable=False),
    Column("period_end", Text, nullable=False),
    Column("content", Text, nullable=False),
    Column("model_used", Text, nullable=False),
    Column("token_count", Integer),
    Column("generated_at", Text, nullable=False, server_default=text("(datetime('now'))")),
    Column("category_id", Integer, ForeignKey("device_categories.id")),
    Index("idx_digests_period", "period_start"),
    Index("idx_digests_type", "digest_type", "period_start"),
)

analysis_batches = Table(
    "analysis_batches", metadata,
    Column("id", Text, primary_key=True),  # UUID
    Column("job_type", Text, nullable=False),  # sentiment, clustering, digest, product_extract
    Column("status", Text, nullable=False, server_default=text("'pending'")),
    Column("post_count", Integer, server_default=text("0")),
    Column("input_tokens", Integer, server_default=text("0")),
    Column("output_tokens", Integer, server_default=text("0")),
    Column("started_at", Text),
    Column("completed_at", Text),
    Column("error_message", Text),
)
