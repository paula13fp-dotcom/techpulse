"""Sentiment analysis job: processes unanalyzed posts in batches via Claude."""
import json
from datetime import datetime, timezone

from sqlalchemy import text

from techpulse.analysis.claude_client import get_claude
from techpulse.database.connection import get_db
from techpulse.database.queries import get_unanalyzed_posts
from techpulse.utils.logger import get_logger

logger = get_logger("analysis.sentiment")

BATCH_SIZE = 20
SYSTEM_PROMPT = """You are a technology sentiment analyzer.
Analyze posts/reviews about phones, smartwatches, and tablets.
Respond ONLY with valid JSON — no markdown, no explanation."""

USER_PROMPT_TEMPLATE = """Analyze the sentiment of these tech posts. For each, determine:
- label: "positive", "negative", "neutral", or "mixed"
- positive_score: float 0.0-1.0
- neutral_score: float 0.0-1.0
- negative_score: float 0.0-1.0
(scores must sum to ~1.0)
- confidence: float 0.0-1.0

Posts:
{posts_json}

Respond with a JSON array:
[{{"id": <post_id>, "label": "...", "positive_score": 0.0, "neutral_score": 0.0, "negative_score": 0.0, "confidence": 0.0}}, ...]"""


def run_sentiment_analysis(limit: int = 100) -> int:
    """Process unanalyzed posts. Returns number of posts analyzed."""
    claude = get_claude()
    if not claude.is_available():
        logger.warning("Claude not available — skipping sentiment analysis")
        return 0

    posts = get_unanalyzed_posts(limit=limit)
    if not posts:
        logger.info("No posts to analyze")
        return 0

    logger.info(f"Analyzing sentiment for {len(posts)} posts")
    analyzed = 0

    # Process in batches
    for i in range(0, len(posts), BATCH_SIZE):
        batch = posts[i:i + BATCH_SIZE]
        results = _analyze_batch(claude, batch)
        if results:
            _save_results(results)
            analyzed += len(results)

    logger.info(f"Sentiment analysis complete: {analyzed} posts processed")
    return analyzed


def _analyze_batch(claude, posts: list[dict]) -> list[dict]:
    posts_json = json.dumps([
        {
            "id": p["id"],
            "title": (p.get("title") or "")[:200],
            "body": (p.get("body") or "")[:500],
        }
        for p in posts
    ], ensure_ascii=False)

    prompt = USER_PROMPT_TEMPLATE.format(posts_json=posts_json)
    response = claude.complete(prompt, system=SYSTEM_PROMPT, job_type="sentiment")

    if not response:
        return []

    try:
        # Strip any accidental markdown
        clean = response.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        results = json.loads(clean)
        return results if isinstance(results, list) else []
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse sentiment response: {e}\nResponse: {response[:200]}")
        return []


def _save_results(results: list[dict]):
    with get_db() as conn:
        for r in results:
            try:
                conn.execute(text("""
                    INSERT OR REPLACE INTO sentiment_results
                    (post_id, label, positive_score, neutral_score, negative_score, confidence, analyzed_at)
                    VALUES (:post_id, :label, :pos, :neu, :neg, :conf, :now)
                """), {
                    "post_id": r["id"],
                    "label": r.get("label", "neutral"),
                    "pos": r.get("positive_score", 0.0),
                    "neu": r.get("neutral_score", 0.0),
                    "neg": r.get("negative_score", 0.0),
                    "conf": r.get("confidence", 0.5),
                    "now": datetime.now(timezone.utc).isoformat(),
                })
            except Exception as e:
                logger.warning(f"Failed to save sentiment for post {r.get('id')}: {e}")
        conn.commit()
