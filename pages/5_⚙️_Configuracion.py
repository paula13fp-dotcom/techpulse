from __future__ import annotations
import os
import streamlit as st
from techpulse.ui_style import inject_css

st.set_page_config(page_title="Configuración · TechPulse", page_icon="⚙️", layout="wide")
from techpulse.auth import require_login; require_login()  # noqa: E702
inject_css()
st.title("⚙️ Configuración")


# ── API Keys status ────────────────────────────────────────────────────────────

st.subheader("🔑 API Keys")
st.caption(
    "Las claves nunca se muestran. Solo se indica si están configuradas o no. "
    "Para modificarlas edita el fichero `.env` (local) o los Secrets en Streamlit Cloud."
)

_KEYS = [
    ("REDDIT_CLIENT_ID",     "Reddit Client ID",     "reddit"),
    ("REDDIT_CLIENT_SECRET", "Reddit Client Secret", "reddit"),
    ("YOUTUBE_API_KEY",      "YouTube Data API v3",  "youtube"),
    ("ANTHROPIC_API_KEY",    "Anthropic (Claude)",   "claude"),
]

cols = st.columns(2)
for i, (env_key, label, _source) in enumerate(_KEYS):
    val = os.getenv(env_key, "")
    ok  = bool(val and not val.startswith("tu_") and len(val) > 8)
    icon = "✅" if ok else "❌"
    cols[i % 2].metric(label, f"{icon} {'Configurada' if ok else 'No configurada'}")

st.divider()

# ── Scheduler info ─────────────────────────────────────────────────────────────

st.subheader("⏰ Scheduler")

col1, col2 = st.columns(2)
col1.info("🔄 **Scrape** — cada 6 horas (Reddit, YouTube, blogs tech, GSMArena…)")
col2.info("🧠 **Análisis Claude** — diariamente a las 07:00 hora España")

try:
    from techpulse.scheduler.job_manager import get_next_run
    next_run = get_next_run()
    if next_run:
        st.success(f"⏭️ Próximo análisis Claude: **{next_run[:16].replace('T', ' ')}**")
except Exception:
    st.caption("Scheduler no disponible en este entorno.")

st.divider()

# ── DB stats ──────────────────────────────────────────────────────────────────

st.subheader("🗄️ Base de datos")

try:
    from techpulse.database.queries import get_post_count, get_source_stats
    from techpulse.database.connection import get_db
    from sqlalchemy import text

    post_count = get_post_count()
    sources    = get_source_stats()

    with get_db() as conn:
        product_count = conn.execute(text("SELECT COUNT(*) as n FROM products")).fetchone().n
        cluster_count = conn.execute(text("SELECT COUNT(*) as n FROM topic_clusters")).fetchone().n
        digest_count  = conn.execute(text("SELECT COUNT(*) as n FROM digests")).fetchone().n

    mc1, mc2, mc3, mc4 = st.columns(4)
    mc1.metric("Posts totales",    f"{post_count:,}")
    mc2.metric("Productos tracked", f"{product_count:,}")
    mc3.metric("Topic clusters",    f"{cluster_count:,}")
    mc4.metric("Resúmenes Claude",  f"{digest_count:,}")

    st.markdown("**Posts por fuente:**")
    import pandas as pd
    df = pd.DataFrame([
        {"Fuente": s["display_name"], "Posts": s["post_count"],
         "Último scrape": (s.get("last_scraped") or "—")[:16]}
        for s in sources
    ])
    st.dataframe(df, use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"Error al leer la BD: {e}")

st.divider()

# ── Streamlit Cloud setup guide ───────────────────────────────────────────────

st.subheader("☁️ Despliegue en Streamlit Cloud")

with st.expander("Ver instrucciones", expanded=False):
    st.markdown("""
**Pasos para publicar TechPulse en Streamlit Cloud (gratis):**

1. **Sube el código a GitHub**
   ```bash
   git init && git add . && git commit -m "TechPulse Streamlit"
   git remote add origin https://github.com/TU_USUARIO/techpulse.git
   git push -u origin main
   ```

2. **Crea una app en [share.streamlit.io](https://share.streamlit.io)**
   - Main file path: `streamlit_app.py`
   - Python version: 3.11

3. **Añade los Secrets** (Settings → Secrets):
   ```toml
   REDDIT_CLIENT_ID     = "tu_id"
   REDDIT_CLIENT_SECRET = "tu_secret"
   YOUTUBE_API_KEY      = "AIza..."
   ANTHROPIC_API_KEY    = "sk-ant-..."
   ```

4. **Usa `requirements_streamlit.txt`** como fichero de dependencias
   (Sin PyQt6 ni Playwright, que no funcionan en el cloud)

> ⚠️ La BD SQLite en Streamlit Cloud es **efímera** — se resetea en cada restart.
> El scrape de blogs RSS funciona sin API keys, así que la app arranca con datos reales rápidamente.
""")

# ── App version ───────────────────────────────────────────────────────────────

st.divider()
st.caption("TechPulse · Streamlit v1.50 · SQLite + APScheduler + Anthropic Claude")
