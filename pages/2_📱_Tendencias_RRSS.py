from __future__ import annotations
import streamlit as st
import pandas as pd
from sqlalchemy import text

from techpulse.database.queries import get_trending_topics, get_feed
from techpulse.database.connection import get_db
from techpulse.ui_style import inject_css

st.set_page_config(page_title="Tendencias RRSS · TechPulse", page_icon="📱", layout="wide")
inject_css()
st.title("📱 Tendencias RRSS")
st.caption(
    "Lo que se está hablando en internet — Reddit · YouTube · Xataka · MuyComputer · "
    "Applesfera · GSMArena · XDA y más."
)

# ── Tabs principales ───────────────────────────────────────────────────────────

tab_tendencias, tab_posts = st.tabs(["🔥 Tendencias", "📰 Posts"])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Tendencias (temas en tendencia + radar de productos)
# ══════════════════════════════════════════════════════════════════════════════

with tab_tendencias:

    # ── Sección 1: Temas en tendencia ──────────────────────────────────────────

    st.subheader("🔥 Temas en tendencia")

    @st.cache_data(ttl=300)
    def _load_trending() -> list[dict]:
        return get_trending_topics(limit=10)

    topics = _load_trending()

    if not topics:
        st.info("Sin clusters de temas todavía. El análisis Claude los genera a las 07:00.")
    else:
        for t in topics:
            hot_badge = " 🔥 **TRENDING**" if t.get("is_trending") else ""
            with st.expander(
                f"{t.get('label', '—')}{hot_badge}  ·  {t.get('post_count', 0)} posts",
                expanded=False,
            ):
                if t.get("description"):
                    st.markdown(t["description"])
                cols2 = st.columns(2)
                if t.get("category_name"):
                    cols2[0].caption(f"Categoría: {t['category_name']}")
                if t.get("product_name"):
                    cols2[1].caption(f"Producto: {t['product_name']}")

    st.divider()

    # ── Sección 2: Radar de productos en conversación ──────────────────────────

    st.subheader("🎯 Radar de productos en conversación")
    st.caption("Productos más mencionados en Reddit, YouTube, blogs y foros — últimos 7 días.")

    _CAT_OPTIONS = [
        "Todas las categorías",
        "📱 Móviles",
        "⌚ Smartwatches",
        "📲 Tablets",
        "💻 Portátiles",
        "🎮 Gaming",
    ]
    _CAT_SLUG_MAP = {
        "📱 Móviles":      "phones",
        "⌚ Smartwatches": "smartwatches",
        "📲 Tablets":      "tablets",
        "💻 Portátiles":   "laptops",
        "🎮 Gaming":       "gaming",
    }

    radar_cat = st.radio(
        "Filtrar por categoría",
        _CAT_OPTIONS,
        horizontal=True,
        key="radar_cat",
    )

    @st.cache_data(ttl=300, show_spinner=False)
    def _load_radar_products() -> list[dict]:
        """Top 20 products by 7-day mentions across all monitored sources."""
        from datetime import datetime, timezone, timedelta
        since_7d  = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        since_30d = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        with get_db() as conn:
            rows = conn.execute(text("""
                SELECT
                    pr.canonical_name,
                    dc.name AS category,
                    COUNT(DISTINCT CASE WHEN p.published_at >= :since_7d  THEN ppm.post_id END) AS mentions_7d,
                    COUNT(DISTINCT CASE WHEN p.published_at >= :since_30d THEN ppm.post_id END) AS mentions_30d,
                    ROUND(AVG(CASE WHEN sr.id IS NOT NULL THEN sr.positive_score * 100 END)) AS avg_pos,
                    ROUND(AVG(CASE WHEN sr.id IS NOT NULL THEN sr.negative_score * 100 END)) AS avg_neg
                FROM products pr
                LEFT JOIN device_categories dc ON dc.id = pr.category_id
                JOIN post_product_mentions ppm ON ppm.product_id = pr.id
                JOIN posts p ON p.id = ppm.post_id
                LEFT JOIN sentiment_results sr ON sr.post_id = p.id
                WHERE p.published_at >= :since_30d
                GROUP BY pr.id
                HAVING mentions_7d > 0
                ORDER BY mentions_7d DESC
                LIMIT 20
            """), {"since_7d": since_7d, "since_30d": since_30d}).fetchall()
        return [dict(r._mapping) for r in rows]

    radar_prods = _load_radar_products()

    if not radar_prods:
        st.info(
            "Sin datos de conversación todavía. Ejecuta **🔄 Actualizar todo** "
            "en el Dashboard para importar posts y analizarlos."
        )
    else:
        total_mentions = sum(r["mentions_7d"] for r in radar_prods)
        top_prod       = radar_prods[0]["canonical_name"] if radar_prods else "—"
        kpi1, kpi2, kpi3 = st.columns(3)
        kpi1.metric("Productos en conversación", len(radar_prods))
        kpi2.metric("Menciones esta semana",      f"{total_mentions:,}")
        kpi3.metric("Producto más mencionado",    top_prod)

        st.divider()

        # Apply category filter
        cat_slug = _CAT_SLUG_MAP.get(radar_cat)
        filtered = radar_prods
        if cat_slug:
            filtered = [r for r in radar_prods if (r.get("category") or "").lower() == cat_slug] or radar_prods

        col_table, col_brands = st.columns([3, 2], gap="large")

        with col_table:
            st.subheader("💬 Productos en conversación")
            rows_display = []
            for r in filtered:
                pos = r.get("avg_pos") or 0
                neg = r.get("avg_neg") or 0
                sentiment_icon = "🟢" if pos > neg and pos > 40 else ("🔴" if neg > pos and neg > 40 else "⚪")
                rows_display.append({
                    "Producto":    r["canonical_name"],
                    "Categoría":  r.get("category") or "—",
                    "7 días":     r["mentions_7d"],
                    "30 días":    r["mentions_30d"],
                    "Sentimiento": f"{sentiment_icon} {pos:.0f}% / {neg:.0f}%",
                })

            df_radar = pd.DataFrame(rows_display)
            st.dataframe(
                df_radar,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "7 días":  st.column_config.NumberColumn("7d",  width="small"),
                    "30 días": st.column_config.NumberColumn("30d", width="small"),
                },
            )

        with col_brands:
            st.subheader("🏷️ Top marcas")
            brand_counts: dict[str, int] = {}
            for r in radar_prods:
                brand = r["canonical_name"].split()[0].strip("()[]")
                brand_counts[brand] = brand_counts.get(brand, 0) + r["mentions_7d"]
            top_brands = sorted(brand_counts.items(), key=lambda x: x[1], reverse=True)[:8]
            if top_brands:
                df_brands = pd.DataFrame(top_brands, columns=["Marca", "Menciones 7d"])
                st.bar_chart(df_brands.set_index("Marca"), horizontal=True, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Posts (feed completo)
# ══════════════════════════════════════════════════════════════════════════════

with tab_posts:

    # ── Search bar ─────────────────────────────────────────────────────────────

    search_query = st.text_input(
        label="search",
        placeholder="🔍  Buscar por término, producto o marca…  (ej: Samsung, Pixel 10a, rumores)",
        label_visibility="collapsed",
        key="feed_search",
    )

    # ── Source list from DB ────────────────────────────────────────────────────

    @st.cache_data(ttl=120)
    def _active_sources() -> list[dict]:
        """All sources that have at least one post."""
        try:
            with get_db() as conn:
                rows = conn.execute(text("""
                    SELECT s.name, s.display_name
                    FROM sources s
                    WHERE EXISTS (SELECT 1 FROM posts p WHERE p.source_id = s.id)
                    ORDER BY s.display_name
                """)).fetchall()
            return [{"name": r.name, "display_name": r.display_name} for r in rows]
        except Exception:
            return []

    # ── Filters ───────────────────────────────────────────────────────────────

    sources = _active_sources()
    source_options = {"Todas las fuentes": None}
    for s in sources:
        source_options[s["display_name"]] = s["name"]

    cat_options = {
        "Todas las categorías": None,
        "📱 Móviles":           "phones",
        "⌚ Smartwatches":       "smartwatches",
        "📲 Tablets":           "tablets",
    }

    col_src, col_cat, col_reset = st.columns([2, 2, 1])
    with col_src:
        src_label = st.selectbox("Fuente", list(source_options.keys()), key="feed_source")
    with col_cat:
        cat_label = st.selectbox("Categoría", list(cat_options.keys()), key="feed_cat")
    with col_reset:
        st.write("")  # spacer
        if st.button("↺ Reset", use_container_width=True):
            st.session_state.feed_source  = "Todas las fuentes"
            st.session_state.feed_cat     = "Todas las categorías"
            st.session_state.feed_search  = ""
            st.session_state.feed_offset  = 0
            st.rerun()

    selected_source = source_options[src_label]
    selected_cat    = cat_options[cat_label]
    search_term     = (search_query or "").strip()

    # ── Pagination ────────────────────────────────────────────────────────────

    PAGE_SIZE = 30
    if "feed_offset" not in st.session_state:
        st.session_state.feed_offset = 0

    filter_key = f"{src_label}|{cat_label}|{search_term}"
    if st.session_state.get("_last_filter") != filter_key:
        st.session_state.feed_offset     = 0
        st.session_state["_last_filter"] = filter_key

    offset = st.session_state.feed_offset

    # ── Load posts ────────────────────────────────────────────────────────────

    @st.cache_data(ttl=60, show_spinner=False)
    def _load_posts(source, cat, search, limit, off):
        return get_feed(source_name=source, category_slug=cat, search=search, limit=limit, offset=off)

    with st.spinner("Cargando posts…"):
        posts = _load_posts(selected_source, selected_cat, search_term or None, PAGE_SIZE, offset)

    # ── Render posts ──────────────────────────────────────────────────────────

    _SENTIMENT_BADGE = {
        "positive": "🟢 Positivo",
        "negative": "🔴 Negativo",
        "neutral":  "⚪ Neutral",
        "mixed":    "🟡 Mixto",
    }

    _SOURCE_ICON = {
        "reddit":      "🤖",
        "youtube":     "▶️",
        "xda":         "🛠️",
        "gsmarena":    "📱",
        "tiktok":      "🎵",
        "xataka":      "⚡",
        "xatakamovil": "📲",
        "muycomputer": "💻",
        "andro4all":   "🤖",
        "hipertextual":"🧪",
        "applesfera":  "🍎",
    }

    if search_term:
        st.markdown(
            f'<p style="color:#6B7280; font-size:0.88em; margin:0 0 0.5rem 0;">'
            f'🔍 Resultados para <strong style="color:#1D1E20;">"{search_term}"</strong> '
            f'— {len(posts)} post{"s" if len(posts) != 1 else ""} encontrado{"s" if len(posts) != 1 else ""}'
            f'{"" if len(posts) < PAGE_SIZE else " (mostrando primeros " + str(PAGE_SIZE) + ")"}'
            f'</p>',
            unsafe_allow_html=True,
        )

    if not posts:
        st.info("No hay posts con los filtros seleccionados." if (selected_source or selected_cat or search_term)
                else "Sin datos todavía. Ve al Dashboard y pulsa 🔄 Actualizar todo.")
    else:
        for post in posts:
            src_name  = post.get("source_name", "")
            src_icon  = _SOURCE_ICON.get(src_name, "📌")
            src_label_display = post.get("source_display") or src_name
            date_str  = (post.get("published_at") or "")[:10]
            score     = post.get("score") or post.get("upvotes") or 0
            comments  = post.get("comment_count") or 0
            sentiment = _SENTIMENT_BADGE.get(post.get("sentiment") or "", "")
            title     = post.get("title") or "(sin título)"
            url       = post.get("url") or ""
            body      = post.get("body") or ""

            with st.container():
                c_left, c_right = st.columns([5, 1])
                with c_left:
                    if url:
                        st.markdown(f"### [{title}]({url})")
                    else:
                        st.markdown(f"### {title}")
                    meta = f"{src_icon} **{src_label_display}**"
                    if date_str:
                        meta += f"  ·  📅 {date_str}"
                    if score:
                        meta += f"  ·  👍 {score:,}"
                    if comments:
                        meta += f"  ·  💬 {comments:,}"
                    if sentiment:
                        meta += f"  ·  {sentiment}"
                    st.caption(meta)
                    if body:
                        st.markdown(
                            f"<span style='color:#9ca3af;font-size:0.9em'>"
                            f"{body[:280]}{'…' if len(body) > 280 else ''}</span>",
                            unsafe_allow_html=True,
                        )
                with c_right:
                    if url:
                        st.link_button("Abrir →", url, use_container_width=True)

            st.divider()

    # ── Pagination controls ───────────────────────────────────────────────────

    p_prev, p_info, p_next = st.columns([1, 2, 1])
    with p_prev:
        if offset > 0:
            if st.button("← Anterior", use_container_width=True):
                st.session_state.feed_offset = max(0, offset - PAGE_SIZE)
                st.rerun()
    with p_info:
        page_num = offset // PAGE_SIZE + 1
        st.markdown(
            f"<p style='text-align:center;color:#9ca3af'>Página {page_num} · "
            f"mostrando {len(posts)} posts</p>",
            unsafe_allow_html=True,
        )
    with p_next:
        if len(posts) == PAGE_SIZE:
            if st.button("Siguiente →", use_container_width=True):
                st.session_state.feed_offset = offset + PAGE_SIZE
                st.rerun()
