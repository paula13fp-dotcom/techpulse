from __future__ import annotations
"""Daily/weekly digest generator using Claude."""
import json
from datetime import datetime, timezone, timedelta

from sqlalchemy import text

from techpulse.analysis.claude_client import get_claude
from techpulse.database.connection import get_db
from techpulse.utils.logger import get_logger

logger = get_logger("analysis.digest")

SYSTEM_PROMPT = """Eres un periodista tecnológico especializado en electrónica de consumo para el mercado español.
Escribe resúmenes claros y atractivos sobre lo que se está hablando en internet sobre móviles,
smartwatches, tablets, portátiles y gaming. Usa formato markdown.
IMPORTANTE: Escribe SIEMPRE en ESPAÑOL, independientemente del idioma de los datos de entrada."""

USER_PROMPT_TEMPLATE = """Genera un resumen tecnológico {period_label} basado en estos datos.

TEMAS EN TENDENCIA:
{topics}

SENTIMIENTO POR PRODUCTO:
{sentiment}

POSTS MÁS COMENTADOS:
{posts}

INTELIGENCIA DE MERCADO (Amazon España + Google Trends):
{market_intel}

Escribe el resumen en markdown con estas secciones en español:
## 🔥 Lo más trending
(3-5 temas calientes con breve explicación)

## 📱 Productos destacados
(2-3 productos más mencionados con resumen de sentimiento)

## 📊 Pulso del mercado
(Solo si hay datos de mercado: top 2-3 productos más vendidos en Amazon + término más buscado en Google España)

## 💬 Conclusiones clave
(3-5 puntos con lo más importante que se está diciendo)

Sé conciso e informativo. Sin relleno. Máximo 700 palabras. Todo en español.
Omite la sección 📊 si no hay datos de mercado disponibles."""


def run_digest(digest_type: str = "daily") -> str | None:
    """Generate a digest. Returns the digest text or None on failure."""
    claude = get_claude()
    if not claude.is_available():
        logger.warning("Claude not available — skipping digest")
        return None

    days_back = 1 if digest_type == "daily" else 7
    since = (datetime.now(timezone.utc) - timedelta(days=days_back)).isoformat()
    period_label = "diario" if digest_type == "daily" else "semanal"

    with get_db() as conn:
        # Trending topics
        topics_rows = conn.execute(text("""
            SELECT label, description, post_count, is_trending
            FROM topic_clusters
            WHERE last_seen_at >= :since
            ORDER BY is_trending DESC, post_count DESC
            LIMIT 10
        """), {"since": since}).fetchall()

        # Product sentiment
        sentiment_rows = conn.execute(text("""
            SELECT pr.canonical_name,
                   COUNT(sr.id) AS mentions,
                   ROUND(AVG(sr.positive_score) * 100) AS positive_pct,
                   ROUND(AVG(sr.negative_score) * 100) AS negative_pct
            FROM products pr
            JOIN post_product_mentions ppm ON ppm.product_id = pr.id
            JOIN sentiment_results sr ON sr.post_id = ppm.post_id
            WHERE sr.analyzed_at >= :since
            GROUP BY pr.id
            ORDER BY mentions DESC
            LIMIT 10
        """), {"since": since}).fetchall()

        # Most discussed posts
        posts_rows = conn.execute(text("""
            SELECT p.title, p.score, p.view_count, s.display_name AS source
            FROM posts p
            JOIN sources s ON p.source_id = s.id
            WHERE p.published_at >= :since
              AND p.title IS NOT NULL
            ORDER BY (COALESCE(p.score, 0) + COALESCE(p.view_count, 0)) DESC
            LIMIT 15
        """), {"since": since}).fetchall()

    topics_text = "\n".join(
        f"- {r.label}: {r.description or ''} ({r.post_count} posts)"
        for r in topics_rows
    ) or "Sin temas disponibles todavía."

    sentiment_text = "\n".join(
        f"- {r.canonical_name}: {r.mentions} menciones, {r.positive_pct}% positivo, {r.negative_pct}% negativo"
        for r in sentiment_rows
    ) or "Sin datos de sentimiento todavía."

    posts_text = "\n".join(
        f"- [{r.source}] {r.title}"
        for r in posts_rows
    ) or "Sin posts disponibles."

    # ── Market intelligence from cache ────────────────────────────────────────
    market_intel_text = "Sin datos de mercado disponibles."
    try:
        from techpulse.scheduler.jobs import load_market_cache
        cache = load_market_cache()
        if cache:
            lines: list[str] = []
            # Amazon bestsellers — top 3 per category
            best = cache.get("amazon_bestsellers", {})
            if best:
                lines.append("Amazon Más Vendidos (Top 3):")
                for cat, prods in best.items():
                    if prods:
                        items = ", ".join(f"#{p['rank']} {p['title'][:40]}" for p in prods[:3])
                        lines.append(f"  {cat}: {items}")
            # Amazon novedades — top 2 per category
            new_rel = cache.get("amazon_new_releases", {})
            if new_rel:
                lines.append("Amazon Novedades Destacadas (Top 2):")
                for cat, prods in new_rel.items():
                    if prods:
                        items = ", ".join(f"{p['title'][:40]}" for p in prods[:2])
                        lines.append(f"  {cat}: {items}")
            # Google Trends — only if data available (manual fetch)
            trends = cache.get("google_trends", {})
            has_trends = any(v.get("top") for v in trends.values())
            if has_trends:
                lines.append("Google Trends España (Top búsquedas):")
                for cat, data in list(trends.items())[:2]:
                    top_qs = [t["query"] for t in data.get("top", [])[:5]]
                    if top_qs:
                        lines.append(f"  {cat}: {', '.join(top_qs)}")
                lines.append("Búsquedas en alza:")
                for cat, data in list(trends.items())[:2]:
                    rising_qs = [r["query"] for r in data.get("rising", [])[:3]]
                    if rising_qs:
                        lines.append(f"  {cat}: {', '.join(rising_qs)}")
            if lines:
                market_intel_text = "\n".join(lines)
    except Exception as e:
        logger.warning(f"Could not load market cache for digest: {e}")

    prompt = USER_PROMPT_TEMPLATE.format(
        period_label=period_label,
        topics=topics_text,
        sentiment=sentiment_text,
        posts=posts_text,
        market_intel=market_intel_text,
    )

    logger.info(f"Generating {period_label} digest...")
    content = claude.complete(prompt, system=SYSTEM_PROMPT, job_type="digest", max_tokens=2048)

    if not content:
        return None

    period_end = datetime.now(timezone.utc)
    period_start = period_end - timedelta(days=days_back)

    with get_db() as conn:
        conn.execute(text("""
            INSERT INTO digests (digest_type, period_start, period_end, content, model_used)
            VALUES (:dtype, :start, :end, :content, :model)
        """), {
            "dtype": digest_type,
            "start": period_start.isoformat(),
            "end": period_end.isoformat(),
            "content": content,
            "model": "claude-sonnet-4-6",
        })
        conn.commit()

    logger.info(f"{period_label.capitalize()} digest generated ({len(content)} chars)")
    return content
