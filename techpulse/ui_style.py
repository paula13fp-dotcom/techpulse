"""PCComponents-inspired CSS theme for TechPulse Streamlit app — light theme."""
from __future__ import annotations
import streamlit as st

# ── PCComponents color palette (light theme) ─────────────────────────────────
# Primary accent — PCComponents orange
PCC_ORANGE     = "#FF6000"
PCC_ORANGE_DK  = "#CC4D00"
PCC_ORANGE_LT  = "#FF8C42"
PCC_ORANGE_XLT = "#FFF0E8"   # very light orange tint for backgrounds

# Sidebar — PCComponents dark navy (mimics their dark nav tiles)
SIDEBAR_BG     = "#170453"
SIDEBAR_MID    = "#1E0B5E"
SIDEBAR_BORDER = "#2D1B69"
SIDEBAR_TEXT   = "#FFFFFF"

# Main content backgrounds (light)
BG_WHITE       = "#FFFFFF"
BG_CARD        = "#FAFAFA"
BG_CARD_ALT    = "#F0F2F5"
BG_ORANGE_TINT = "#FFF7F2"

# Text
TEXT_DARK      = "#1D1E20"
TEXT_MED       = "#4B5563"
TEXT_MUTED     = "#6B7280"
TEXT_LIGHT     = "#9CA3AF"

# Borders
BORDER         = "#E5E7EB"
BORDER_MED     = "#D1D5DB"
BORDER_ORANGE  = "#FFCFB3"

# Status
PCC_GREEN      = "#059669"   # green — in catalog / positive
PCC_RED        = "#DC2626"   # red — not in catalog
PCC_AMBER      = "#D97706"   # amber — warning / neutral

# Aliases kept for backward compat in pages that import them
PCC_PURPLE     = BG_CARD
PCC_PURPLE_MID = BG_CARD_ALT
PCC_BORDER     = BORDER
PCC_WHITE      = BG_WHITE
PCC_GRAY_LT    = TEXT_MED
PCC_GRAY_MD    = TEXT_MUTED


def inject_css() -> None:
    """Inject PCComponents-inspired CSS (light theme) into the current Streamlit page."""
    st.markdown(f"""
<style>
/* ═══════════════════════════════════════════════════════════════════════════
   GLOBAL BACKGROUNDS — white content, dark sidebar
═══════════════════════════════════════════════════════════════════════════ */
[data-testid="stAppViewContainer"],
.main {{
    background-color: {BG_WHITE};
}}
[data-testid="block-container"] {{
    padding-top: 1.5rem;
    background-color: {BG_WHITE};
}}

/* ═══════════════════════════════════════════════════════════════════════════
   SIDEBAR — dark navy (PCComponents nav style)
═══════════════════════════════════════════════════════════════════════════ */
[data-testid="stSidebar"],
[data-testid="stSidebarContent"] {{
    background-color: {SIDEBAR_BG};
    border-right: none;
}}
[data-testid="stSidebarNavItems"] a,
[data-testid="stSidebarNavItems"] span {{
    color: rgba(255,255,255,0.75) !important;
    border-radius: 6px;
    padding: 6px 12px;
    font-weight: 500;
    transition: all 0.15s ease;
}}
[data-testid="stSidebarNavItems"] a:hover {{
    color: {PCC_ORANGE} !important;
    background-color: {SIDEBAR_MID} !important;
}}
[data-testid="stSidebarNavItems"] a[aria-current="page"] {{
    color: {PCC_ORANGE} !important;
    background-color: {SIDEBAR_MID} !important;
    border-left: 3px solid {PCC_ORANGE};
    font-weight: 700;
}}
/* App name at top of sidebar */
[data-testid="stSidebarHeader"] {{
    background-color: {SIDEBAR_BG};
    border-bottom: 1px solid {SIDEBAR_BORDER};
}}
[data-testid="stSidebarHeader"] a,
[data-testid="stSidebarHeader"] span,
[data-testid="stSidebarHeader"] p {{
    color: {SIDEBAR_TEXT} !important;
}}

/* ═══════════════════════════════════════════════════════════════════════════
   TOP HEADER BAR
═══════════════════════════════════════════════════════════════════════════ */
[data-testid="stHeader"] {{
    background-color: {BG_WHITE};
    border-bottom: 1px solid {BORDER};
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}}
[data-testid="stDecoration"] {{
    background-image: linear-gradient(90deg, {PCC_ORANGE}, {PCC_ORANGE_LT});
    height: 3px;
}}

/* ═══════════════════════════════════════════════════════════════════════════
   TYPOGRAPHY
═══════════════════════════════════════════════════════════════════════════ */
h1 {{
    color: {PCC_ORANGE} !important;
    font-weight: 800 !important;
    letter-spacing: -0.02em;
    padding-bottom: 0.25em;
    border-bottom: 2px solid {BORDER_ORANGE};
    margin-bottom: 0.5rem !important;
}}
h2 {{
    color: {TEXT_DARK} !important;
    font-weight: 700 !important;
    letter-spacing: -0.01em;
}}
h3 {{
    color: {TEXT_DARK} !important;
    font-weight: 600 !important;
}}
p, li {{
    color: {TEXT_MED};
}}

/* ═══════════════════════════════════════════════════════════════════════════
   METRIC CARDS
═══════════════════════════════════════════════════════════════════════════ */
[data-testid="stMetric"] {{
    background-color: {BG_WHITE};
    border: 1px solid {BORDER};
    border-radius: 10px;
    padding: 14px 16px !important;
    border-top: 3px solid {PCC_ORANGE};
    box-shadow: 0 1px 4px rgba(0,0,0,0.05);
}}
[data-testid="stMetricValue"] {{
    color: {PCC_ORANGE} !important;
    font-weight: 800 !important;
    font-size: 1.6rem !important;
}}
[data-testid="stMetricLabel"] {{
    color: {TEXT_MUTED} !important;
    font-size: 0.72em !important;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    font-weight: 600;
}}
[data-testid="stMetricDelta"] {{
    color: {PCC_GREEN} !important;
    font-weight: 600;
}}

/* ═══════════════════════════════════════════════════════════════════════════
   BUTTONS
═══════════════════════════════════════════════════════════════════════════ */
.stButton > button {{
    background-color: {PCC_ORANGE} !important;
    color: {BG_WHITE} !important;
    border: none !important;
    border-radius: 6px !important;
    font-weight: 700 !important;
    letter-spacing: 0.02em;
    transition: background 0.18s ease, transform 0.1s ease, box-shadow 0.18s ease;
    box-shadow: 0 2px 8px rgba(255,96,0,0.25);
}}
.stButton > button:hover {{
    background-color: {PCC_ORANGE_DK} !important;
    transform: translateY(-1px);
    box-shadow: 0 4px 14px rgba(255,96,0,0.35);
}}
.stButton > button:active {{
    transform: translateY(0);
    box-shadow: 0 1px 4px rgba(255,96,0,0.2);
}}
.stButton > button[kind="secondary"],
.stButton > button[data-testid="baseButton-secondary"] {{
    background-color: {BG_WHITE} !important;
    border: 2px solid {PCC_ORANGE} !important;
    color: {PCC_ORANGE} !important;
    box-shadow: none;
}}
.stButton > button[kind="secondary"]:hover {{
    background-color: {PCC_ORANGE_XLT} !important;
}}
.stLinkButton a {{
    background-color: {BG_CARD} !important;
    color: {PCC_ORANGE} !important;
    border: 1px solid {BORDER_ORANGE} !important;
    border-radius: 6px !important;
    font-weight: 600 !important;
}}
.stLinkButton a:hover {{
    background-color: {PCC_ORANGE} !important;
    color: {BG_WHITE} !important;
}}

/* ═══════════════════════════════════════════════════════════════════════════
   TABS
═══════════════════════════════════════════════════════════════════════════ */
.stTabs [data-baseweb="tab-list"] {{
    background-color: {BG_CARD};
    border-bottom: 2px solid {BORDER};
    gap: 2px;
    padding: 0 4px;
    border-radius: 8px 8px 0 0;
}}
.stTabs [data-baseweb="tab"] {{
    color: {TEXT_MUTED} !important;
    font-weight: 600;
    padding: 0.55em 1.3em;
    border-radius: 6px 6px 0 0;
    transition: all 0.15s ease;
    border-bottom: 3px solid transparent;
    background-color: transparent;
}}
.stTabs [data-baseweb="tab"]:hover {{
    color: {TEXT_DARK} !important;
    background-color: {BG_CARD_ALT} !important;
}}
.stTabs [aria-selected="true"] {{
    color: {PCC_ORANGE} !important;
    background-color: {BG_WHITE} !important;
    border-bottom: 3px solid {PCC_ORANGE} !important;
}}
.stTabs [data-baseweb="tab-panel"] {{
    background-color: {BG_WHITE};
    padding-top: 1rem;
}}

/* ═══════════════════════════════════════════════════════════════════════════
   CONTAINERS & EXPANDERS
═══════════════════════════════════════════════════════════════════════════ */
[data-testid="stVerticalBlockBorderWrapper"] > div > div {{
    border: 1px solid {BORDER} !important;
    border-radius: 10px !important;
    background-color: {BG_WHITE} !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.05);
}}
[data-testid="stExpander"] {{
    border: 1px solid {BORDER} !important;
    border-radius: 10px !important;
    background-color: {BG_WHITE} !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04);
    overflow: hidden;
}}
[data-testid="stExpander"] summary {{
    background-color: {BG_CARD} !important;
    color: {TEXT_DARK} !important;
    font-weight: 600;
}}
[data-testid="stExpander"] summary:hover {{
    background-color: {BG_CARD_ALT} !important;
    color: {PCC_ORANGE} !important;
}}
[data-testid="stExpander"] svg {{
    fill: {PCC_ORANGE} !important;
}}

/* ═══════════════════════════════════════════════════════════════════════════
   PROGRESS BARS
═══════════════════════════════════════════════════════════════════════════ */
[data-testid="stProgressBar"] > div > div > div > div {{
    background: linear-gradient(90deg, {PCC_ORANGE}, {PCC_ORANGE_LT}) !important;
    border-radius: 4px;
}}
[data-testid="stProgressBar"] > div > div > div {{
    background-color: {BG_CARD_ALT} !important;
    border-radius: 4px;
}}

/* ═══════════════════════════════════════════════════════════════════════════
   DATAFRAMES
═══════════════════════════════════════════════════════════════════════════ */
[data-testid="stDataFrame"] {{
    border: 1px solid {BORDER} !important;
    border-radius: 10px;
    overflow: hidden;
    box-shadow: 0 1px 4px rgba(0,0,0,0.05);
}}
[data-testid="stDataFrame"] thead th {{
    background-color: {BG_CARD} !important;
    color: {PCC_ORANGE} !important;
    font-weight: 700;
    text-transform: uppercase;
    font-size: 0.75em;
    letter-spacing: 0.05em;
    border-bottom: 2px solid {BORDER_ORANGE} !important;
}}
[data-testid="stDataFrame"] tbody tr:hover {{
    background-color: {BG_ORANGE_TINT} !important;
}}

/* ═══════════════════════════════════════════════════════════════════════════
   INPUTS & SELECTS
═══════════════════════════════════════════════════════════════════════════ */
[data-baseweb="select"] > div,
[data-baseweb="input"] > div {{
    background-color: {BG_WHITE} !important;
    border-color: {BORDER_MED} !important;
    color: {TEXT_DARK} !important;
    border-radius: 6px !important;
}}
[data-baseweb="select"] > div:focus-within,
[data-baseweb="input"] > div:focus-within {{
    border-color: {PCC_ORANGE} !important;
    box-shadow: 0 0 0 2px rgba(255,96,0,0.15) !important;
}}
[data-baseweb="menu"] {{
    background-color: {BG_WHITE} !important;
    border: 1px solid {BORDER} !important;
    border-radius: 8px !important;
    box-shadow: 0 4px 16px rgba(0,0,0,0.1) !important;
}}
[data-baseweb="option"]:hover {{
    background-color: {PCC_ORANGE_XLT} !important;
    color: {PCC_ORANGE} !important;
}}

/* ═══════════════════════════════════════════════════════════════════════════
   ALERTS
═══════════════════════════════════════════════════════════════════════════ */
[data-testid="stAlert"] {{
    border-radius: 8px !important;
    border-left-width: 4px !important;
}}

/* ═══════════════════════════════════════════════════════════════════════════
   DIVIDERS & CAPTIONS
═══════════════════════════════════════════════════════════════════════════ */
hr {{
    border-color: {BORDER} !important;
    border-top-width: 1px !important;
    opacity: 1;
}}
[data-testid="stCaptionContainer"] p, small {{
    color: {TEXT_MUTED} !important;
}}

/* ═══════════════════════════════════════════════════════════════════════════
   STATUS / SPINNER
═══════════════════════════════════════════════════════════════════════════ */
[data-testid="stStatusWidget"] {{
    background-color: {BG_WHITE} !important;
    border: 1px solid {BORDER} !important;
    border-radius: 10px !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.07);
}}

/* ═══════════════════════════════════════════════════════════════════════════
   BAR CHART
═══════════════════════════════════════════════════════════════════════════ */
[data-testid="stArrowVegaLiteChart"] canvas,
[data-testid="stVegaLiteChart"] canvas {{
    border-radius: 8px;
}}

/* ═══════════════════════════════════════════════════════════════════════════
   CUSTOM PRODUCT CARD CLASSES (used via unsafe_allow_html)
═══════════════════════════════════════════════════════════════════════════ */
.pcc-card {{
    background-color: {BG_WHITE};
    border: 1px solid {BORDER};
    border-radius: 10px;
    padding: 16px 20px;
    margin: 8px 0;
    transition: border-color 0.15s ease, box-shadow 0.15s ease;
    box-shadow: 0 1px 4px rgba(0,0,0,0.05);
}}
.pcc-card:hover {{
    border-color: {BORDER_ORANGE};
    box-shadow: 0 4px 16px rgba(255,96,0,0.1);
}}
.pcc-card-gap {{
    border-left: 4px solid {PCC_ORANGE} !important;
}}
.pcc-card-catalog {{
    border-left: 4px solid {PCC_GREEN} !important;
}}
.pcc-score-big {{
    font-size: 2.4rem;
    font-weight: 900;
    line-height: 1;
}}
.pcc-pill {{
    display: inline-block;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 0.72em;
    font-weight: 700;
    letter-spacing: 0.04em;
}}
.pcc-pill-orange {{ background-color: #FFF0E8; color: {PCC_ORANGE};  border: 1px solid {BORDER_ORANGE}; }}
.pcc-pill-green  {{ background-color: #ECFDF5; color: {PCC_GREEN};  border: 1px solid #A7F3D0; }}
.pcc-pill-gray   {{ background-color: {BG_CARD}; color: {TEXT_MUTED}; border: 1px solid {BORDER}; }}
.pcc-pill-red    {{ background-color: #FEF2F2; color: {PCC_RED};   border: 1px solid #FECACA; }}
.pcc-pill-amber  {{ background-color: #FFFBEB; color: {PCC_AMBER}; border: 1px solid #FDE68A; }}
</style>
""", unsafe_allow_html=True)


# ── Reusable HTML helpers ────────────────────────────────────────────────────

def kpi_strip(metrics: list[dict]) -> None:
    """Render a row of KPI cards. Each dict: {label, value, icon?, delta?}"""
    cols = st.columns(len(metrics))
    for col, m in zip(cols, metrics):
        col.metric(
            label=f"{m.get('icon', '')} {m['label']}",
            value=m["value"],
            delta=m.get("delta"),
        )


def vel_pill(m7: int, mp7: int) -> str:
    """Return an HTML velocity pill based on week-over-week change."""
    if mp7 == 0:
        if m7 > 0:
            return '<span class="pcc-pill pcc-pill-orange">🆕 NUEVO</span>'
        return '<span class="pcc-pill pcc-pill-gray">→ Sin datos</span>'
    growth = (m7 - mp7) / mp7
    pct = int(growth * 100)
    if pct >= 200:
        return f'<span class="pcc-pill pcc-pill-red">🚀 +{pct}%</span>'
    if pct >= 50:
        return f'<span class="pcc-pill pcc-pill-orange">↑↑ +{pct}%</span>'
    if pct >= 10:
        return f'<span class="pcc-pill pcc-pill-green">↑ +{pct}%</span>'
    if pct >= -10:
        return f'<span class="pcc-pill pcc-pill-gray">→ {pct:+d}%</span>'
    return f'<span class="pcc-pill pcc-pill-gray">↓ {pct}%</span>'


def score_badge_html(score: int) -> str:
    """Large score badge HTML for light theme."""
    if score >= 70:
        color, label = PCC_ORANGE, "Alta oportunidad"
    elif score >= 45:
        color, label = PCC_AMBER, "Oportunidad media"
    else:
        color, label = TEXT_MUTED, "Baja oportunidad"
    return (
        f'<div style="text-align:center; padding:8px 12px; background:#FFF7F2; '
        f'border:1px solid {BORDER_ORANGE}; border-radius:8px;">'
        f'  <div class="pcc-score-big" style="color:{color};">{score}</div>'
        f'  <div style="font-size:0.68em; color:{TEXT_MUTED}; text-transform:uppercase; '
        f'letter-spacing:0.05em;">/100 · {label}</div>'
        f'</div>'
    )


def section_header(title: str, subtitle: str = "") -> None:
    """Styled section header with optional subtitle."""
    html = (
        f'<div style="margin: 1.5rem 0 0.75rem 0; padding-bottom: 0.5rem; '
        f'border-bottom: 1px solid {BORDER};">'
        f'  <span style="font-size:1.1rem; font-weight:700; color:{TEXT_DARK};">{title}</span>'
    )
    if subtitle:
        html += (
            f'  <span style="font-size:0.82rem; color:{TEXT_MUTED}; '
            f'margin-left:10px;">{subtitle}</span>'
        )
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)
