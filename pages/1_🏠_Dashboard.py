from __future__ import annotations
import streamlit as st

from techpulse.database.queries import (
    get_latest_digest, get_post_count,
)
from techpulse.ui_style import inject_css

st.set_page_config(page_title="Dashboard · TechPulse", page_icon="🏠", layout="wide")
from techpulse.auth import require_login; require_login()  # noqa: E702
inject_css()
st.title("🏠 Análisis")


# ── Helpers ───────────────────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def _load() -> dict:
    return {
        "digest":     get_latest_digest("daily"),
        "post_count": get_post_count(),
    }


# ── Header + single action button ─────────────────────────────────────────────

col_hdr, col_btn = st.columns([4, 1])
with col_hdr:
    st.markdown("Monitorización de tendencias tech en tiempo real.")
with col_btn:
    if st.button("🔄 Actualizar todo", type="primary", use_container_width=True):
        with st.spinner("Ejecutando pipeline completo…  (puede tardar varios minutos)"):
            try:
                from techpulse.scheduler.jobs import run_full_pipeline
                result = run_full_pipeline()
                st.cache_data.clear()
                st.success(
                    f"✅ {result['posts']} posts nuevos · "
                    f"{result['sentiment']} analizados · "
                    f"{result['clusters']} clusters"
                )
            except Exception as e:
                st.error(f"Error en el pipeline: {e}")
        st.rerun()

data = _load()

# ── Daily digest ──────────────────────────────────────────────────────────────
st.subheader("📰 Análisis")
digest = data["digest"]

if not digest:
    st.info(
        "El resumen diario se genera automáticamente a las 07:00 (hora España). "
        "Requiere créditos Anthropic activos."
    )
else:
    st.caption(f"Generado el {digest.get('generated_at', '')[:10]}")
    # Strip the H1 title that Claude includes at the top of the digest
    content = digest.get("content", "")
    lines = content.splitlines()
    if lines and lines[0].startswith("# "):
        content = "\n".join(lines[1:]).lstrip("\n")
    st.markdown(content)
