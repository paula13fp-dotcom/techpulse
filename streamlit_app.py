# TechPulse — Streamlit entry point
# 1. Inyectar st.secrets como env vars (Streamlit Cloud compat)
# 2. Inicializar la BD una sola vez
# 3. Arrancar el scheduler en background
# 4. Mostrar la página de inicio
from __future__ import annotations
import os

import streamlit as st
from techpulse.ui_style import inject_css

# ── 1. Secrets bridge ────────────────────────────────────────────────────────
# En Streamlit Cloud los secrets NO se exponen automáticamente como env vars.
# Los inyectamos aquí para que settings.py (que usa os.getenv) funcione igual.
try:
    for _k, _v in st.secrets.items():
        if isinstance(_v, str):
            os.environ.setdefault(_k, _v)
except Exception:
    pass  # local: las variables ya vienen de .env

# ── 2. Página config ─────────────────────────────────────────────────────────
st.set_page_config(
    page_title="TechPulse",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── 3. Boot (singleton por proceso) ─────────────────────────────────────────
@st.cache_resource
def _boot() -> bool:
    """Init DB + Playwright browsers + start scheduler. Runs once per server process."""
    import subprocess, sys

    # Instalar browsers de Playwright si no están disponibles (Streamlit Cloud)
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            p.chromium.launch()   # smoke-test: falla si el browser no está instalado
    except Exception:
        subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            check=False, capture_output=True,
        )

    from techpulse.database.connection import init_db
    init_db()
    try:
        from techpulse.scheduler.job_manager import start_scheduler
        start_scheduler()
    except Exception as e:
        st.warning(f"Scheduler no iniciado: {e}")
    return True


_boot()

# ── 4. Auth gate ──────────────────────────────────────────────────────────
from techpulse.auth import require_login  # noqa: E402
require_login()

inject_css()

# ── 5. Home page ─────────────────────────────────────────────────────────────
st.title("📡 TechPulse")
st.markdown(
    "**Monitorización de tendencias tech en tiempo real** — "
    "Reddit · YouTube · Xataka · MuyComputer · Applesfera · GSMArena · XDA y más."
)

st.divider()

col1, col2, col3 = st.columns(3)
with col1:
    st.page_link("pages/1_🏠_Analisis_optimizado.py",     label="🏠 Análisis optimizado",         icon="🏠")
with col2:
    st.page_link("pages/2_📱_Tendencias_RRSS.py",        label="📱 Tendencias RRSS",             icon="📱")
with col3:
    st.page_link("pages/3_📊_Tendencias_Busqueda.py",    label="📊 Tendencias Búsqueda y Venta", icon="📊")

st.divider()

# ── Stats rápidas ─────────────────────────────────────────────────────────────
from techpulse.database.queries import get_post_count, get_source_stats  # noqa: E402

post_count = get_post_count()
sources    = get_source_stats()

st.subheader("Estado actual")
cols = st.columns(min(len(sources) + 1, 6))
cols[0].metric("Total posts", f"{post_count:,}")
for i, s in enumerate(sources[:5], start=1):
    cols[i].metric(s["display_name"], str(s["post_count"]))

if post_count == 0:
    st.info(
        "💡 La base de datos está vacía. "
        "Ve al **Dashboard** y pulsa **🔄 Actualizar todo** para importar datos."
    )
