from __future__ import annotations
import json
import streamlit as st
import pandas as pd
from pathlib import Path
from techpulse.ui_style import inject_css

st.set_page_config(page_title="Tendencias Búsqueda · TechPulse", page_icon="📊", layout="wide")
inject_css()
st.title("📊 Tendencias Búsqueda y Venta")
st.caption(
    "Google Trends España · Amazon Bestsellers · Amazon Novedades · Google Keyword Planner — "
    "señales de demanda en tiempo real."
)

# ── Cache helpers ──────────────────────────────────────────────────────────────

_CACHE_FILE = Path(__file__).parent.parent / "techpulse" / "data" / "market_cache.json"
_KWP_CACHE  = Path(__file__).parent.parent / "techpulse" / "data" / "kwp_cache.json"


def _load_market_cache() -> dict:
    try:
        if _CACHE_FILE.exists():
            return json.loads(_CACHE_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _save_market_cache(cache: dict) -> None:
    try:
        _CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        _CACHE_FILE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def _load_kwp_cache() -> dict:
    try:
        if _KWP_CACHE.exists():
            return json.loads(_KWP_CACHE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _save_kwp_cache(cache: dict) -> None:
    try:
        _KWP_CACHE.parent.mkdir(parents=True, exist_ok=True)
        _KWP_CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


# ── Shared category selector ───────────────────────────────────────────────────

_CATEGORIES = [
    "📱 Móviles",
    "⌚ Smartwatches",
    "📲 Tablets",
    "💻 Portátiles",
    "🎮 Gaming",
]

category = st.radio(
    "Categoría",
    _CATEGORIES,
    horizontal=True,
    key="market_cat",
)

st.divider()

# ── Tabs ──────────────────────────────────────────────────────────────────────

tab_trends, tab_amazon, tab_kwp = st.tabs([
    "📊 Google Trends",
    "🛍️ Amazon",
    "🔑 Keyword Planner",
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Google Trends
# ══════════════════════════════════════════════════════════════════════════════

_TRENDS_KEYWORDS: dict[str, list[str]] = {
    "📱 Móviles": [
        "iphone 16", "iphone 16 pro", "iphone 17", "iphone 17 pro",
        "samsung galaxy s25", "samsung galaxy s25 ultra", "samsung galaxy s26",
        "google pixel 9", "google pixel 9 pro", "google pixel 10",
        "xiaomi 15", "oneplus 13", "nothing phone 3",
        "samsung galaxy a55", "samsung galaxy a35", "samsung galaxy a16",
        "xiaomi redmi note 14", "xiaomi poco x7", "xiaomi poco f7",
        "realme 13 pro", "oppo reno 13",
        "samsung galaxy z fold 7", "samsung galaxy z flip 7", "móvil plegable",
        "mejor móvil 2026", "mejor móvil calidad precio 2026",
        "móvil barato bueno", "móvil segunda mano", "comprar smartphone",
        "móvil 5g", "cambiar de móvil",
    ],
    "⌚ Smartwatches": [
        "apple watch series 10", "apple watch series 11", "apple watch ultra 2",
        "samsung galaxy watch 7", "samsung galaxy watch 8", "samsung galaxy ring",
        "google pixel watch 3", "google pixel watch 4",
        "garmin fenix 8", "garmin forerunner", "garmin venu 3",
        "huawei watch gt 4", "amazfit gts 4", "xiaomi smart band 9",
        "anillo inteligente", "smart ring",
        "mejor smartwatch 2026", "smartwatch barato", "smartwatch hombre",
        "smartwatch mujer", "reloj deportivo gps", "pulsera actividad",
        "smartwatch para correr", "reloj inteligente android",
    ],
    "📲 Tablets": [
        "ipad pro m4", "ipad pro m5", "ipad air m2", "ipad air m3", "ipad mini",
        "samsung galaxy tab s10", "samsung galaxy tab s10 ultra", "samsung galaxy tab s11",
        "xiaomi pad 7", "xiaomi pad 6", "lenovo tab p12", "lenovo tab plus",
        "amazon fire hd", "realme pad",
        "mejor tablet 2026", "tablet barata buena", "tablet android",
        "tablet para dibujar", "tablet para niños", "tablet para estudiar",
        "tablet 10 pulgadas", "tablet con teclado", "tablet para ver netflix",
    ],
    "💻 Portátiles": [
        "macbook pro", "macbook air m3", "macbook air m4",
        "portátil inteligencia artificial", "copilot plus pc",
        "snapdragon x elite", "portátil qualcomm",
        "dell xps 15", "asus zenbook", "hp spectre", "lenovo thinkpad",
        "microsoft surface pro", "acer swift",
        "portátil gaming", "asus rog", "razer blade", "lenovo legion",
        "msi gaming", "portátil rtx 4070",
        "mejor portátil 2026", "portátil barato estudiante",
        "portátil trabajo", "portátil ligero",
        "portátil i7", "portátil 16 pulgadas", "ultrabook",
    ],
    "🎮 Gaming": [
        "ps5 pro", "xbox series x", "nintendo switch 2",
        "nintendo switch 2 precio", "steam deck oled", "asus rog ally",
        "rtx 5090", "rtx 5080", "rtx 5070", "rtx 5060",
        "amd rx 9070", "amd rx 9070 xt",
        "ryzen 9 9950x", "intel core ultra 9",
        "monitor gaming 1440p", "monitor gaming 4k", "monitor 240hz",
        "teclado mecánico gaming", "teclado gaming inalámbrico",
        "ratón gaming", "auriculares gaming",
        "mejor pc gaming 2026", "pc gaming barato", "tarjeta gráfica 2026",
        "gaming setup",
    ],
}


@st.cache_data(ttl=1800, show_spinner=False)
def _fetch_trends(cat: str, kws: tuple[str, ...]) -> dict:
    from pytrends.request import TrendReq
    import time as _time
    import random

    pt = TrendReq(hl="es-ES", tz=60, timeout=(10, 30))
    all_top:    list[dict] = []
    all_rising: list[dict] = []

    # Use only the first 15 keywords to reduce API calls and avoid rate limits
    kws = kws[:15]
    consecutive_errors = 0

    for i in range(0, len(kws), 5):
        chunk = list(kws[i: i + 5])

        # Retry up to 2 times with exponential backoff
        success = False
        for attempt in range(3):
            try:
                pt.build_payload(chunk, timeframe="now 7-d", geo="ES")
                related = pt.related_queries()
                for kw, data in related.items():
                    top_df    = data.get("top")
                    rising_df = data.get("rising")
                    if top_df is not None and not top_df.empty:
                        for _, row in top_df.head(12).iterrows():
                            all_top.append({
                                "Búsqueda":        str(row["query"]).title(),
                                "Interés (0-100)": int(row["value"]),
                                "Término origen":  kw,
                            })
                    if rising_df is not None and not rising_df.empty:
                        for _, row in rising_df.head(12).iterrows():
                            val = row["value"]
                            val_str = (
                                "🔥 Breakout (+5000%+)"
                                if isinstance(val, str)
                                else f"+{int(val):,}%"
                            )
                            all_rising.append({
                                "Búsqueda":       str(row["query"]).title(),
                                "Crecimiento":    val_str,
                                "Valor":          int(val) if isinstance(val, (int, float)) else 999999,
                                "Término origen": kw,
                            })
                success = True
                consecutive_errors = 0
                break
            except Exception as e:
                err_str = str(e).lower()
                if "429" in err_str or "too many" in err_str:
                    # Rate limited — wait longer before retrying
                    wait = (attempt + 1) * 5 + random.uniform(1, 3)
                    _time.sleep(wait)
                else:
                    break  # Non-rate-limit error, skip this chunk

        if not success:
            consecutive_errors += 1
            # If 2 consecutive chunks fail, stop to avoid hammering Google
            if consecutive_errors >= 2:
                break

        if i + 5 < len(kws):
            # Random delay 3-6s between batches to avoid rate limits
            _time.sleep(3 + random.uniform(0, 3))

    seen_top: dict[str, dict] = {}
    for item in all_top:
        key = item["Búsqueda"].lower()
        if key not in seen_top or item["Interés (0-100)"] > seen_top[key]["Interés (0-100)"]:
            seen_top[key] = item

    seen_rising: dict[str, dict] = {}
    for item in all_rising:
        key = item["Búsqueda"].lower()
        if key not in seen_rising or item["Valor"] > seen_rising[key]["Valor"]:
            seen_rising[key] = item

    top_sorted    = sorted(seen_top.values(),    key=lambda x: x["Interés (0-100)"], reverse=True)[:20]
    rising_sorted = sorted(seen_rising.values(), key=lambda x: x["Valor"],           reverse=True)[:20]

    for item in rising_sorted:
        item.pop("Valor", None)

    return {"top": top_sorted, "rising": rising_sorted}


def _render_trends(top: list, rising: list, category: str) -> None:
    col_top, col_rising = st.columns(2, gap="large")
    with col_top:
        st.subheader("📈 Búsquedas más populares")
        st.caption("Interés relativo en los últimos 7 días (España) — 100 = máximo")
        if top:
            df_top = pd.DataFrame(top)[["Búsqueda", "Interés (0-100)"]]
            st.dataframe(
                df_top,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Interés (0-100)": st.column_config.ProgressColumn(
                        "Interés", min_value=0, max_value=100, format="%d"
                    ),
                },
            )
    with col_rising:
        st.subheader("🚀 Términos en alza")
        st.caption("Mayor crecimiento de búsquedas esta semana en España")
        if rising:
            df_rising = pd.DataFrame(rising)[["Búsqueda", "Crecimiento"]]
            st.dataframe(df_rising, use_container_width=True, hide_index=True)

    # AI analysis
    if top or rising:
        top_kws    = tuple(t["Búsqueda"] for t in top[:5])
        rising_kws = tuple(r["Búsqueda"] for r in rising[:5])

        @st.cache_data(ttl=1800, show_spinner=False)
        def _trends_ai_analysis(cat: str, top_kws: tuple, rising_kws: tuple) -> str:
            try:
                from techpulse.analysis.claude_client import get_claude
                claude = get_claude()
                if not claude.is_available():
                    return ""
                prompt = (
                    f"Analiza estas tendencias de búsqueda en Google España para {cat} (últimos 7 días).\n"
                    f"Top búsquedas: {', '.join(top_kws)}\n"
                    f"Términos en alza: {', '.join(rising_kws)}\n\n"
                    "En 3-4 frases explica qué está ocurriendo en el mercado tech español, "
                    "qué impulsa estas búsquedas y qué implica para el sector. "
                    "Sé directo y concreto, sin introducciones genéricas."
                )
                return claude.complete(prompt, max_tokens=300) or ""
            except Exception:
                return ""

        analysis = _trends_ai_analysis(category, top_kws, rising_kws)
        if analysis:
            st.info(f"🤖 **Análisis IA:** {analysis}")


with tab_trends:
    st.caption(
        "Búsquedas relacionadas en Google España — últimos 7 días. "
        "Datos en tiempo real sin API key (pytrends)."
    )

    # Load cached Trends data for this category
    mkt_cache   = _load_market_cache()
    cached_data = mkt_cache.get("google_trends", {}).get(category, {})
    cached_at   = mkt_cache.get("updated_at", "")[:16].replace("T", " ")

    col_btn, col_note = st.columns([1, 4])
    with col_btn:
        refresh_trends = st.button("🔄 Actualizar", key="refresh_trends", use_container_width=True)
    with col_note:
        if cached_at:
            st.caption(f"Último análisis: {cached_at} UTC · Caché 30 min para respetar límites de Google.")
        else:
            st.caption("Caché 30 min para respetar límites de Google Trends.")

    if refresh_trends:
        st.cache_data.clear()
        keywords = _TRENDS_KEYWORDS[category]
        with st.spinner(f"Consultando Google Trends para {category}…"):
            try:
                fresh = _fetch_trends(category, tuple(keywords))
                # Persist result to market_cache.json
                mkt_cache = _load_market_cache()
                if "google_trends" not in mkt_cache:
                    mkt_cache["google_trends"] = {}
                mkt_cache["google_trends"][category] = {
                    "top":    [{"query": t["Búsqueda"], "value": t["Interés (0-100)"]} for t in fresh["top"]],
                    "rising": [{"query": r["Búsqueda"], "value": 0} for r in fresh["rising"]],
                }
                mkt_cache["updated_at"] = __import__("datetime").datetime.utcnow().isoformat() + "Z"
                _save_market_cache(mkt_cache)
                cached_data = fresh
                st.rerun()
            except Exception as e:
                st.error(f"Error al consultar Google Trends: {e}")

    top    = cached_data.get("top",    [])
    rising = cached_data.get("rising", [])

    # Normalise: cache stores {query, value}, UI needs {Búsqueda, Interés/Crecimiento}
    if top and "query" in top[0]:
        top = [{"Búsqueda": t["query"].title(), "Interés (0-100)": t.get("value", 0)} for t in top]
    if rising and "query" in rising[0]:
        rising = [{"Búsqueda": r["query"].title(), "Crecimiento": "—"} for r in rising]

    if not top and not rising:
        st.info(
            "No hay datos guardados para esta categoría. "
            "Pulsa **🔄 Actualizar** para consultar Google Trends."
        )
    else:
        _render_trends(top, rising, category)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Amazon (Bestsellers + Novedades)
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=7200, show_spinner=False)
def _fetch_amazon_bestsellers(category_label: str) -> tuple[list[dict], str | None]:
    from techpulse.scrapers.amazon_scraper import get_bestsellers
    products, error = get_bestsellers(category_label, limit=20)
    return [
        {"Pos.": p.rank, "Producto": p.title, "Precio": p.price, "Valoración": p.rating, "url": p.url}
        for p in products
    ], error


@st.cache_data(ttl=7200, show_spinner=False)
def _fetch_amazon_new_releases(category_label: str) -> tuple[list[dict], str | None]:
    from techpulse.scrapers.amazon_scraper import get_new_releases
    products, error = get_new_releases(category_label, limit=20)
    return [
        {"Pos.": p.rank, "Producto": p.title, "Precio": p.price, "Valoración": p.rating, "url": p.url}
        for p in products
    ], error


def _cache_to_amazon_rows(prods: list[dict]) -> list[dict]:
    """Convert market_cache product dicts to UI rows."""
    return [
        {"Pos.": p.get("rank", i + 1), "Producto": p.get("title", ""), "Precio": p.get("price", ""), "Valoración": p.get("rating", ""), "url": ""}
        for i, p in enumerate(prods)
    ]


def _render_amazon_table(rows: list[dict], section_key: str) -> None:
    df_amz = pd.DataFrame(rows)[["Pos.", "Producto", "Precio", "Valoración"]]
    st.dataframe(
        df_amz,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Pos.":       st.column_config.NumberColumn("Pos.", width="small"),
            "Producto":   st.column_config.TextColumn("Producto",   width="large"),
            "Precio":     st.column_config.TextColumn("Precio",     width="small"),
            "Valoración": st.column_config.TextColumn("Valoración", width="small"),
        },
    )
    urls = [r for r in rows if r.get("url")]
    if urls:
        with st.expander("🔗 Ver links directos a Amazon"):
            for r in urls[:10]:
                st.markdown(f"**#{r['Pos.']}** [{r['Producto'][:80]}]({r['url']})")


with tab_amazon:
    mkt_cache   = _load_market_cache()
    cache_ts    = mkt_cache.get("updated_at", "")[:16].replace("T", " ")
    st.caption(
        f"Top 20 de **Amazon España** — Más Vendidos y Novedades por categoría. "
        + (f"Último pipeline: {cache_ts} UTC · " if cache_ts else "")
        + "Caché 2 horas · Sin API key."
    )

    sub_best, sub_new = st.tabs(["🏆 Más Vendidos", "🆕 Novedades"])

    # ── Sub-tab: Más Vendidos ──────────────────────────────────────────────────
    with sub_best:
        col_b1, col_b2 = st.columns([1, 4])
        with col_b1:
            load_best = st.button("🔄 Actualizar", key="load_bestsellers", use_container_width=True)
        with col_b2:
            st.caption("Top 20 productos más vendidos en Amazon España ahora mismo.")

        best_key = f"amz_best_{category}"

        # Auto-load from market_cache if available and not already in session
        if best_key not in st.session_state:
            cached_prods = mkt_cache.get("amazon_bestsellers", {}).get(category, [])
            if cached_prods:
                st.session_state[best_key] = {"rows": _cache_to_amazon_rows(cached_prods), "error": None}

        if load_best:
            _fetch_amazon_bestsellers.clear()
            with st.spinner(f"Cargando más vendidos — {category}…"):
                rows, err = _fetch_amazon_bestsellers(category)
                st.session_state[best_key] = {"rows": rows, "error": err}

        best_data = st.session_state.get(best_key)
        if best_data is None:
            st.info("Pulsa **🔄 Actualizar** para cargar el ranking de más vendidos de Amazon España.")
        else:
            err  = best_data.get("error")
            rows = best_data.get("rows", [])
            if err:
                st.error(f"⚠️ {err}")
            elif not rows:
                st.warning("No se encontraron productos. Prueba a recargar.")
            else:
                st.success(f"✅ {len(rows)} productos más vendidos — {category}")
                _render_amazon_table(rows, "best")

    # ── Sub-tab: Novedades ─────────────────────────────────────────────────────
    with sub_new:
        col_n1, col_n2 = st.columns([1, 4])
        with col_n1:
            load_new = st.button("🔄 Actualizar", key="load_new_releases", use_container_width=True)
        with col_n2:
            st.caption("Últimos lanzamientos con más ventas en Amazon España.")

        new_key = f"amz_new_{category}"

        # Auto-load from market_cache if available and not already in session
        if new_key not in st.session_state:
            cached_new = mkt_cache.get("amazon_new_releases", {}).get(category, [])
            if cached_new:
                st.session_state[new_key] = {"rows": _cache_to_amazon_rows(cached_new), "error": None}

        if load_new:
            _fetch_amazon_new_releases.clear()
            with st.spinner(f"Cargando novedades — {category}…"):
                rows, err = _fetch_amazon_new_releases(category)
                st.session_state[new_key] = {"rows": rows, "error": err}

        new_data = st.session_state.get(new_key)
        if new_data is None:
            st.info("Pulsa **🔄 Actualizar** para ver los últimos lanzamientos en Amazon España.")
        else:
            err  = new_data.get("error")
            rows = new_data.get("rows", [])
            if err:
                st.error(f"⚠️ {err}")
            elif not rows:
                st.warning("No se encontraron productos. Prueba a recargar.")
            else:
                st.success(f"✅ {len(rows)} novedades — {category}")
                _render_amazon_table(rows, "new")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — Google Keyword Planner
# ══════════════════════════════════════════════════════════════════════════════

with tab_kwp:
    from techpulse.scrapers.keyword_planner import (
        credentials_available, missing_credentials,
        generate_keyword_ideas, SEED_KEYWORDS_BY_CATEGORY,
    )

    st.caption(
        "Volúmenes de búsqueda mensuales reales en España vía **Google Ads API**. "
        "Requiere configuración de credenciales (gratuito)."
    )

    if not credentials_available():
        missing = missing_credentials()
        st.warning(
            f"⚙️ Credenciales de Google Ads no configuradas — "
            f"faltan: `{'`, `'.join(missing)}`"
        )
        with st.expander("📋 Instrucciones de configuración", expanded=True):
            st.markdown("""
**Pasos para activar Google Keyword Planner (gratuito):**

1. **Crea un proyecto en Google Cloud**
   → [console.cloud.google.com](https://console.cloud.google.com) → Nuevo proyecto

2. **Activa la Google Ads API**
   → APIs & Services → Library → busca "Google Ads API" → Activar

3. **Crea credenciales OAuth2**
   → APIs & Services → Credentials → Create → OAuth client ID → **Desktop app**
   → Descarga el JSON y anota `client_id` y `client_secret`

4. **Obtén un developer token de Google Ads** *(1-2 días de aprobación)*
   → Crea una cuenta de Google Ads Manager (MCC) gratuita
   → [developers.google.com/google-ads/api/docs/first-call/dev-token](https://developers.google.com/google-ads/api/docs/first-call/dev-token)

5. **Genera el refresh token** (una vez):
   ```bash
   pip install google-auth-oauthlib
   python -m techpulse.scrapers.keyword_planner  # (instrucciones en consola)
   ```

6. **Añade al fichero `.env`:**
   ```
   GOOGLE_ADS_DEVELOPER_TOKEN=...
   GOOGLE_ADS_CLIENT_ID=...
   GOOGLE_ADS_CLIENT_SECRET=...
   GOOGLE_ADS_REFRESH_TOKEN=...
   GOOGLE_ADS_CUSTOMER_ID=1234567890
   ```

7. **Instala la librería:**
   ```bash
   pip install google-ads
   ```
""")
    else:
        default_seeds = SEED_KEYWORDS_BY_CATEGORY.get(category, [])

        seed_input = st.text_area(
            "Keywords semilla (una por línea)",
            value="\n".join(default_seeds),
            height=130,
            key="kwp_seeds",
            help="Google Ads generará ideas relacionadas + volumen de búsqueda para cada una.",
        )

        col_kwp_btn, col_kwp_info = st.columns([1, 3])
        with col_kwp_btn:
            run_kwp = st.button(
                "🔑 Consultar Keyword Planner",
                key="run_kwp",
                type="primary",
                use_container_width=True,
            )
        with col_kwp_info:
            st.caption(
                "Devuelve búsquedas mensuales promedio en España + nivel de competencia. "
                "Sin límite de uso dentro de la cuota de Google Ads."
            )

        # Auto-load last saved results for this category
        kwp_cache = _load_kwp_cache()
        kwp_key   = f"kwp_{category}"
        if kwp_key not in st.session_state and category in kwp_cache:
            st.session_state["kwp_results"] = kwp_cache[category]

        if run_kwp:
            seeds = [s.strip() for s in seed_input.splitlines() if s.strip()]
            if not seeds:
                st.warning("Introduce al menos una keyword semilla.")
            else:
                with st.spinner("Consultando Google Ads Keyword Planner…"):
                    ideas, err = generate_keyword_ideas(seeds, limit=50)
                    result = {
                        "ideas": [
                            {
                                "keyword":             i.keyword,
                                "avg_monthly_searches": i.avg_monthly_searches,
                                "searches_display":    i.searches_display,
                                "competition_label":   i.competition_label,
                                "competition_index":   i.competition_index,
                            } for i in (ideas or [])
                        ],
                        "error": err,
                    }
                    st.session_state["kwp_results"] = result
                    # Persist to kwp_cache.json
                    kwp_cache[category] = result
                    _save_kwp_cache(kwp_cache)

        kwp_data = st.session_state.get("kwp_results")
        if kwp_data:
            err   = kwp_data.get("error")
            ideas_raw = kwp_data.get("ideas", [])

            if err:
                st.error(f"⚠️ {err}")
            elif not ideas_raw:
                st.warning("Sin resultados — prueba con otras keywords semilla.")
            else:
                st.success(f"✅ {len(ideas_raw)} keywords encontradas para España")

                df_kwp = pd.DataFrame([{
                    "Keyword":             i["keyword"] if isinstance(i, dict) else i.keyword,
                    "Búsquedas/mes":       i["avg_monthly_searches"] if isinstance(i, dict) else i.avg_monthly_searches,
                    "Búsquedas (display)": i["searches_display"] if isinstance(i, dict) else i.searches_display,
                    "Competencia":         i["competition_label"] if isinstance(i, dict) else i.competition_label,
                    "Índice competencia":  i["competition_index"] if isinstance(i, dict) else i.competition_index,
                } for i in ideas_raw])

                col_a, col_b = st.columns(2, gap="large")
                with col_a:
                    st.subheader("📈 Mayor volumen de búsqueda")
                    df_top = df_kwp.head(20)[["Keyword", "Búsquedas/mes", "Competencia"]]
                    st.dataframe(
                        df_top,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "Búsquedas/mes": st.column_config.ProgressColumn(
                                "Búsquedas/mes",
                                min_value=0,
                                max_value=int(df_kwp["Búsquedas/mes"].max() or 1),
                                format="%d",
                            ),
                        },
                    )
                with col_b:
                    st.subheader("🟢 Menor competencia (oportunidades)")
                    df_low = (
                        df_kwp[df_kwp["Competencia"].str.contains("Baja", na=False)]
                        .sort_values("Búsquedas/mes", ascending=False)
                        .head(20)[["Keyword", "Búsquedas/mes", "Competencia"]]
                    )
                    if df_low.empty:
                        st.info("No hay keywords de competencia baja en este conjunto.")
                    else:
                        st.dataframe(
                            df_low,
                            use_container_width=True,
                            hide_index=True,
                            column_config={
                                "Búsquedas/mes": st.column_config.ProgressColumn(
                                    "Búsquedas/mes",
                                    min_value=0,
                                    max_value=int(df_kwp["Búsquedas/mes"].max() or 1),
                                    format="%d",
                                ),
                            },
                        )
