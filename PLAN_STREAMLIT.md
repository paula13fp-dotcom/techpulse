# Plan: Migración TechPulse → Streamlit

## Principio clave
**El backend NO se toca.** Todo lo que ya funciona (scrapers, BD, queries, scheduler,
análisis Claude) se reutiliza tal cual. Solo se crean archivos nuevos.

---

## Archivos nuevos (8 ficheros)

```
techpulse/
├── streamlit_app.py                  ← entrada principal (home)
├── pages/
│   ├── 1_🏠_Dashboard.py
│   ├── 2_📰_Feed.py
│   ├── 3_🛒_PCComponents.py
│   ├── 4_📊_Google_Trends.py
│   └── 5_⚙️_Configuracion.py
└── .streamlit/
    ├── config.toml                   ← tema oscuro
    └── secrets.toml.example          ← plantilla de API keys
```

---

## Detalle por fichero

### `streamlit_app.py`
- `st.set_page_config(layout="wide", page_icon="📡")`
- Inyecta `st.secrets` en `os.environ` para que `settings.py` funcione igual en cloud
- Arranca `init_db()` + `start_scheduler()` como `@st.cache_resource` (singleton)
- Muestra home: logo, descripción, botón "🔄 Scrape ahora" con `st.spinner()`

### `.streamlit/config.toml`
```toml
[theme]
base = "dark"
primaryColor      = "#7C3AED"   # accent morado actual
backgroundColor   = "#0F1117"
secondaryBackgroundColor = "#1A1D27"
textColor         = "#E8EAF6"
```

### `pages/1_🏠_Dashboard.py`
- `@st.cache_data(ttl=300)` en todas las queries (get_trending_topics, get_product_sentiment, etc.)
- Fila superior: `st.metric()` cards con post count por fuente
- Dos columnas:
  - Izq: Lista de trending topics (st.expander por topic)
  - Der: Tabla de sentimiento por producto con st.progress() por barra
- Abajo: digest diario en st.info() / st.markdown()

### `pages/2_📰_Feed.py`
- Filtros con `st.selectbox` (fuente dinámica desde DB, categoría)
- Paginación con `st.session_state.feed_offset` + botones ← →
- Cada post: `st.container()` con título linkado, badge de fuente, score, sentimiento
- `st.divider()` entre posts

### `pages/3_🛒_PCComponents.py`
- Sección superior: Brand Radar siempre visible (st.bar_chart de marcas por menciones_7d)
- Botón "📡 Analizar tendencias"
- Al pulsar: `with st.status("Analizando...", expanded=True)` — muestra progreso producto a producto
- Resultados guardados en `st.session_state.radar_results`
- Dos secciones con `st.tabs(["🚨 Oportunidades", "📈 En catálogo"])`:
  - Oportunidades: cards con opportunity score, velocity, source breakdown, snippet
  - En catálogo: cards con precio, stock, botón "Ver →"

### `pages/4_📊_Google_Trends.py`
- `st.radio` horizontal para categoría (Móviles / Smartwatches / Tablets)
- Botón "🔄 Actualizar" — `st.spinner()` mientras carga pytrends
- Datos en `st.session_state.trends_data` (persiste al cambiar de pestaña)
- Dos columnas:
  - Izq: Top búsquedas como dataframe con barra de porcentaje
  - Der: Términos en alza con badge de % crecimiento

### `pages/5_⚙️_Configuracion.py`
- Muestra qué secrets/env vars están configurados (solo ✅/❌, nunca el valor)
- Instrucciones para configurar en Streamlit Cloud (link a docs)
- Intervalo de scrape actual, próximo análisis Claude
- Info: versión app, total posts en BD

---

## Secrets bridge (en streamlit_app.py)

```python
# Inyectar st.secrets como env vars para compatibilidad con settings.py
try:
    import streamlit as st
    import os
    for k, v in st.secrets.items():
        if isinstance(v, str):
            os.environ.setdefault(k, v)
except Exception:
    pass  # local: ya vienen de .env
```

Esto hace que `settings.py` funcione sin modificaciones en cloud.

---

## `.streamlit/secrets.toml.example`
```toml
REDDIT_CLIENT_ID     = "tu_client_id"
REDDIT_CLIENT_SECRET = "tu_client_secret"
REDDIT_USER_AGENT    = "TechPulse/1.0"
YOUTUBE_API_KEY      = "AIza..."
ANTHROPIC_API_KEY    = "sk-ant-..."
```

---

## Consideraciones Streamlit Cloud

| Aspecto | Solución |
|---|---|
| SQLite efímero | Aceptable para prototipo; scrape rápido de blogs al arrancar |
| TikTok (Playwright) | Skip graceful — try/except en jobs.py |
| API keys | st.secrets → os.environ bridge |
| Scheduler | @st.cache_resource → arranca 1 vez por proceso servidor |
| Dependencias PyQt6 | Añadir `packages.txt` con `libgl1-mesa-glx` o excluir PyQt6 del cloud requirements |

Para cloud: crear `requirements_streamlit.txt` sin PyQt6/TikTokApi/playwright.

---

## Orden de implementación

1. `.streamlit/config.toml` + `secrets.toml.example`
2. `streamlit_app.py` (boot + home)
3. `pages/1_🏠_Dashboard.py`
4. `pages/2_📰_Feed.py`
5. `pages/3_🛒_PCComponents.py` (más compleja)
6. `pages/4_📊_Google_Trends.py`
7. `pages/5_⚙️_Configuracion.py`
8. `requirements_streamlit.txt` (sin PyQt6)

Tiempo estimado: ~1 sesión de implementación.
