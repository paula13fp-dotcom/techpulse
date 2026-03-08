"""Topic clustering: groups posts into themes using Claude."""
import json
from datetime import datetime, timezone, timedelta

from sqlalchemy import text

from techpulse.analysis.claude_client import get_claude
from techpulse.database.connection import get_db
from techpulse.utils.logger import get_logger

logger = get_logger("analysis.clustering")

SYSTEM_PROMPT = """Eres un analista de tendencias tecnológicas especializado en el mercado español.
Agrupa posts sobre móviles, tablets, smartwatches, portátiles y gaming en clusters temáticos.
Responde ÚNICAMENTE con JSON válido, sin explicaciones ni markdown adicional.
IMPORTANTE: Escribe SIEMPRE el label y la description en ESPAÑOL."""

USER_PROMPT_TEMPLATE = """Agrupa estos posts tecnológicos en 5-10 clusters temáticos distintos.
Los posts pueden estar en cualquier idioma — analiza su contenido y agrúpalos.
Para cada cluster indica:
- label: nombre descriptivo corto en español (máx. 60 caracteres), ej: "Problemas de batería Samsung Galaxy S25"
- description: resumen de 1-2 frases en español explicando de qué trata el cluster
- post_ids: lista de IDs de posts que pertenecen a este cluster
- is_trending: true si el cluster tiene mucho engagement o es un tema muy activo

Posts:
{posts_json}

Responde con JSON:
{{"clusters": [{{"label": "...", "description": "...", "post_ids": [...], "is_trending": false}}, ...]}}"""


def run_clustering(days_back: int = 3) -> int:
    """Cluster recent posts. Returns number of clusters created."""
    claude = get_claude()
    if not claude.is_available():
        logger.warning("Claude not available — skipping clustering")
        return 0

    since = (datetime.now(timezone.utc) - timedelta(days=days_back)).isoformat()

    with get_db() as conn:
        rows = conn.execute(text("""
            SELECT p.id, p.title, p.body, p.score, p.view_count
            FROM posts p
            WHERE p.published_at >= :since
              AND (p.title IS NOT NULL OR p.body IS NOT NULL)
            ORDER BY (p.score + p.view_count) DESC
            LIMIT 100
        """), {"since": since}).fetchall()

    if not rows:
        logger.info("No posts to cluster")
        return 0

    posts = [dict(r._mapping) for r in rows]
    logger.info(f"Clustering {len(posts)} posts")

    posts_json = json.dumps([
        {
            "id": p["id"],
            "title": (p.get("title") or "")[:150],
            "body": (p.get("body") or "")[:300],
        }
        for p in posts
    ], ensure_ascii=False)

    response = claude.complete(
        USER_PROMPT_TEMPLATE.format(posts_json=posts_json),
        system=SYSTEM_PROMPT,
        job_type="clustering",
        max_tokens=4096,
    )
    if not response:
        return 0

    try:
        clean = response.strip()
        if clean.startswith("```"):
            clean = "\n".join(clean.split("\n")[1:-1])
        data = json.loads(clean)
        clusters = data.get("clusters", [])
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse clustering response: {e}")
        return 0

    now = datetime.now(timezone.utc).isoformat()
    saved = 0

    with get_db() as conn:
        for cluster in clusters:
            try:
                result = conn.execute(text("""
                    INSERT INTO topic_clusters
                    (label, description, post_count, first_seen_at, last_seen_at, is_trending)
                    VALUES (:label, :desc, :count, :now, :now, :trending)
                """), {
                    "label": cluster.get("label", "Unknown topic")[:100],
                    "desc": cluster.get("description", ""),
                    "count": len(cluster.get("post_ids", [])),
                    "now": now,
                    "trending": 1 if cluster.get("is_trending") else 0,
                })
                cluster_id = result.lastrowid

                for post_id in cluster.get("post_ids", []):
                    conn.execute(text("""
                        INSERT OR IGNORE INTO cluster_posts (cluster_id, post_id, relevance)
                        VALUES (:cid, :pid, 1.0)
                    """), {"cid": cluster_id, "pid": post_id})

                saved += 1
            except Exception as e:
                logger.warning(f"Failed to save cluster: {e}")
        conn.commit()

    logger.info(f"Created {saved} topic clusters")
    return saved
