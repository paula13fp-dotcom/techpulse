from __future__ import annotations
"""Google Trends screen — top & rising search terms in Spain for tech categories."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
    QFrame, QPushButton, QSizePolicy,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QDateTime

from techpulse.ui.theme import COLORS


# --------------------------------------------------------------------------- #
# Keywords per category to query in Google Trends
# --------------------------------------------------------------------------- #

_KEYWORDS: dict[str, list[str]] = {
    "phones": [
        "iphone 16", "iphone 17", "samsung galaxy s25", "samsung galaxy s26",
        "xiaomi 15", "google pixel 9", "oneplus 13", "huawei pura 70",
        "nothing phone 3", "motorola edge 50",
        "mejor móvil 2025", "mejor móvil calidad precio", "móvil barato bueno",
        "comprar smartphone", "móvil plegable",
        "smartphone android", "móvil 5g", "cambiar de móvil",
    ],
    "smartwatches": [
        "apple watch series 10", "apple watch ultra 2",
        "samsung galaxy watch 7", "huawei watch gt 4",
        "garmin fenix 7", "garmin forerunner", "polar pacer pro",
        "amazfit gts 4", "xiaomi smart band 9", "fitbit sense",
        "mejor smartwatch 2025", "smartwatch barato", "smartwatch mujer",
        "reloj deportivo gps", "pulsera actividad",
        "reloj inteligente android", "smartwatch para correr",
    ],
    "tablets": [
        "ipad pro", "ipad air", "ipad mini",
        "samsung galaxy tab s9", "samsung galaxy tab s10",
        "xiaomi pad 6", "lenovo tab p12", "amazon fire hd",
        "mejor tablet 2025", "tablet barata buena", "tablet android",
        "tablet para dibujar", "tablet para niños",
        "tablet 10 pulgadas", "tablet con teclado",
    ],
    "laptops": [
        "macbook pro", "macbook air m3", "lenovo thinkpad",
        "dell xps 15", "asus zenbook", "hp spectre",
        "acer swift", "microsoft surface pro",
        "portátil gaming", "asus rog", "razer blade", "lenovo legion",
        "mejor portátil 2025", "portátil barato estudiante",
        "portátil trabajo", "ultrabook",
        "portátil i7", "portátil rtx", "portátil 16 pulgadas",
    ],
    "gaming": [
        "ps5 pro", "xbox series x", "nintendo switch 2",
        "steam deck", "asus rog ally",
        "rtx 5090", "rtx 5080", "ryzen 9 9950x",
        "tarjeta gráfica 2025", "procesador gaming",
        "teclado mecánico gaming", "ratón gaming", "monitor gaming 4k",
        "auriculares gaming", "silla gaming",
        "mejor pc gaming 2025", "pc gaming barato", "gaming setup",
    ],
}

_CATEGORY_LABELS = {
    "phones":      "📱 Móviles",
    "smartwatches":"⌚ Smartwatches",
    "tablets":     "📲 Tablets",
    "laptops":     "💻 Portátiles",
    "gaming":      "🎮 Gaming",
}


# --------------------------------------------------------------------------- #
# Background worker
# --------------------------------------------------------------------------- #

class _TrendsWorker(QThread):
    """Fetches Google Trends data for a set of keywords (Spain, last 7 days)."""
    done = pyqtSignal(dict)   # {"top": [...], "rising": [...]}
    error = pyqtSignal(str)

    def __init__(self, keywords: list[str]):
        super().__init__()
        self.keywords = keywords

    def run(self):
        try:
            from pytrends.request import TrendReq
            import time

            pt = TrendReq(hl="es-ES", tz=60, timeout=(10, 25))

            all_top: list[dict] = []
            all_rising: list[dict] = []

            # pytrends max 5 keywords per request — batch in chunks of 5
            for i in range(0, len(self.keywords), 5):
                chunk = self.keywords[i : i + 5]
                try:
                    pt.build_payload(chunk, timeframe="now 7-d", geo="ES")
                    related = pt.related_queries()

                    for kw, data in related.items():
                        top_df = data.get("top")
                        rising_df = data.get("rising")

                        if top_df is not None and not top_df.empty:
                            for _, row in top_df.head(10).iterrows():
                                all_top.append({
                                    "query": str(row["query"]).title(),
                                    "value": int(row["value"]),
                                    "seed_keyword": kw,
                                })

                        if rising_df is not None and not rising_df.empty:
                            for _, row in rising_df.head(10).iterrows():
                                val = row["value"]
                                # pytrends returns "Breakout" (>5000%) as a string for big spikes
                                val_str = (
                                    "🔥 Breakout" if isinstance(val, str)
                                    else f"+{int(val):,}%"
                                )
                                all_rising.append({
                                    "query": str(row["query"]).title(),
                                    "value": val_str,
                                    "value_raw": int(val) if isinstance(val, (int, float)) else 999999,
                                    "seed_keyword": kw,
                                })

                    if i + 5 < len(self.keywords):
                        time.sleep(1.2)  # polite rate limit between batches

                except Exception as e:
                    # One chunk failed — continue with others
                    continue

            # Deduplicate by query text, keep highest value
            top_dedup: dict[str, dict] = {}
            for item in all_top:
                q = item["query"].lower()
                if q not in top_dedup or item["value"] > top_dedup[q]["value"]:
                    top_dedup[q] = item

            rising_dedup: dict[str, dict] = {}
            for item in all_rising:
                q = item["query"].lower()
                if q not in rising_dedup or item["value_raw"] > rising_dedup[q].get("value_raw", 0):
                    rising_dedup[q] = item

            sorted_top = sorted(top_dedup.values(), key=lambda x: x["value"], reverse=True)[:20]
            sorted_rising = sorted(rising_dedup.values(), key=lambda x: x.get("value_raw", 0), reverse=True)[:20]

            self.done.emit({"top": sorted_top, "rising": sorted_rising})

        except Exception as e:
            self.error.emit(str(e))


# --------------------------------------------------------------------------- #
# Widgets
# --------------------------------------------------------------------------- #

class _SectionHeader(QLabel):
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setStyleSheet(
            f"font-size: 13px; font-weight: bold; color: {COLORS['text_muted']}; "
            f"padding: 8px 0 4px 0; border-bottom: 1px solid {COLORS['border']};"
        )


class _TopTermRow(QFrame):
    """Row showing a popular search term with a proportional bar."""

    def __init__(self, rank: int, query: str, value: int, max_value: int, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 3, 0, 3)
        layout.setSpacing(10)

        # Rank
        rank_lbl = QLabel(f"{rank:2d}.")
        rank_lbl.setFixedWidth(26)
        rank_lbl.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px;")
        layout.addWidget(rank_lbl)

        # Query text
        query_lbl = QLabel(f"🔍 {query}")
        query_lbl.setFixedWidth(260)
        query_lbl.setStyleSheet("font-size: 13px;")
        layout.addWidget(query_lbl)

        # Bar
        bar_container = QWidget()
        bar_container.setFixedHeight(14)
        bar_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        bar = QFrame(bar_container)
        bar_w = max(6, int((value / max(max_value, 1)) * 180))
        bar.setGeometry(0, 1, bar_w, 12)

        # Gradient: green for high, orange for mid, muted for low
        if value >= 80:
            bar_color = COLORS["accent"]
        elif value >= 40:
            bar_color = COLORS["positive"]
        else:
            bar_color = COLORS["text_muted"]
        bar.setStyleSheet(f"background: {bar_color}; border-radius: 3px;")

        layout.addWidget(bar_container)

        # Value
        val_lbl = QLabel(str(value))
        val_lbl.setFixedWidth(40)
        val_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        val_lbl.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
        layout.addWidget(val_lbl)


class _RisingTermRow(QFrame):
    """Row showing a rising search term with its growth label."""

    def __init__(self, rank: int, query: str, value_str: str, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 3, 0, 3)
        layout.setSpacing(10)

        # Rank
        rank_lbl = QLabel(f"{rank:2d}.")
        rank_lbl.setFixedWidth(26)
        rank_lbl.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px;")
        layout.addWidget(rank_lbl)

        # Query text
        query_lbl = QLabel(f"↑ {query}")
        query_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        query_lbl.setStyleSheet("font-size: 13px;")
        layout.addWidget(query_lbl)

        # Growth badge
        is_breakout = "Breakout" in value_str
        badge_color = "#ff4500" if is_breakout else COLORS["positive"]
        growth_lbl = QLabel(value_str)
        growth_lbl.setStyleSheet(
            f"color: {badge_color}; font-size: 12px; font-weight: bold;"
        )
        layout.addWidget(growth_lbl)


# --------------------------------------------------------------------------- #
# Main screen
# --------------------------------------------------------------------------- #

class GoogleTrendsScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker: _TrendsWorker | None = None
        self._active_category = "phones"
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(16)

        # ── Header ───────────────────────────────────────────────────────────
        header = QHBoxLayout()
        title = QLabel("Google Trends España")
        title.setObjectName("title")
        header.addWidget(title)
        header.addStretch()

        self._refresh_btn = QPushButton("🔄 Actualizar")
        self._refresh_btn.clicked.connect(self._start_fetch)
        header.addWidget(self._refresh_btn)
        outer.addLayout(header)

        desc = QLabel(
            "Términos y búsquedas más realizadas en Google España relacionados "
            "con tecnología — actualizado en tiempo real desde Google Trends."
        )
        desc.setObjectName("muted")
        desc.setWordWrap(True)
        outer.addWidget(desc)

        self._status_lbl = QLabel("Selecciona una categoría y pulsa Actualizar.")
        self._status_lbl.setObjectName("muted")
        outer.addWidget(self._status_lbl)

        # ── Category tabs ─────────────────────────────────────────────────────
        tabs_row = QHBoxLayout()
        tabs_row.setSpacing(8)
        self._tab_buttons: dict[str, QPushButton] = {}

        for slug, label in _CATEGORY_LABELS.items():
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setChecked(slug == self._active_category)
            btn.setObjectName("nav_btn")
            btn.clicked.connect(lambda _, s=slug: self._switch_category(s))
            self._tab_buttons[slug] = btn
            tabs_row.addWidget(btn)

        tabs_row.addStretch()
        outer.addLayout(tabs_row)

        # ── Scroll results ────────────────────────────────────────────────────
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)

        self._results_widget = QWidget()
        self._results_layout = QVBoxLayout(self._results_widget)
        self._results_layout.setSpacing(6)
        self._results_layout.setContentsMargins(0, 0, 0, 0)
        self._results_layout.addStretch()

        self._scroll.setWidget(self._results_widget)
        outer.addWidget(self._scroll)

    # ── Category tabs ─────────────────────────────────────────────────────────

    def _switch_category(self, slug: str):
        self._active_category = slug
        for s, btn in self._tab_buttons.items():
            btn.setChecked(s == slug)
        self._start_fetch()

    # ── Data fetching ──────────────────────────────────────────────────────────

    def _start_fetch(self):
        if self._worker and self._worker.isRunning():
            return

        keywords = _KEYWORDS.get(self._active_category, [])
        self._refresh_btn.setEnabled(False)
        self._refresh_btn.setText("Cargando…")
        cat_label = _CATEGORY_LABELS.get(self._active_category, self._active_category)
        self._status_lbl.setText(f"Consultando Google Trends para {cat_label}…")
        self._clear_results()

        self._worker = _TrendsWorker(keywords)
        self._worker.done.connect(self._on_data)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _clear_results(self):
        while self._results_layout.count() > 1:
            item = self._results_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    # ── Rendering ─────────────────────────────────────────────────────────────

    def _on_data(self, data: dict):
        self._refresh_btn.setEnabled(True)
        self._refresh_btn.setText("🔄 Actualizar")

        top: list[dict] = data.get("top", [])
        rising: list[dict] = data.get("rising", [])

        now = QDateTime.currentDateTime().toString("HH:mm")
        self._status_lbl.setText(
            f"Última actualización: {now} · "
            f"{len(top)} términos top · {len(rising)} en alza"
        )

        pos = 0  # insert before stretch

        # ── TOP searches ──────────────────────────────────────────────────────
        if top:
            hdr = _SectionHeader("📈  Búsquedas más populares (últimos 7 días, España)")
            self._results_layout.insertWidget(pos, hdr)
            pos += 1

            max_val = top[0]["value"] if top else 100
            for rank, item in enumerate(top, start=1):
                row = _TopTermRow(rank, item["query"], item["value"], max_val)
                self._results_layout.insertWidget(pos, row)
                pos += 1

            spacer = QLabel("")
            spacer.setFixedHeight(12)
            self._results_layout.insertWidget(pos, spacer)
            pos += 1

        # ── RISING searches ───────────────────────────────────────────────────
        if rising:
            hdr2 = _SectionHeader("🚀  Términos en alza — mayor crecimiento esta semana")
            self._results_layout.insertWidget(pos, hdr2)
            pos += 1

            for rank, item in enumerate(rising, start=1):
                row = _RisingTermRow(rank, item["query"], item["value"])
                self._results_layout.insertWidget(pos, row)
                pos += 1

        if not top and not rising:
            empty = QLabel("No se obtuvieron datos. Google Trends puede limitar peticiones temporalmente.")
            empty.setObjectName("muted")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._results_layout.insertWidget(0, empty)

    def _on_error(self, msg: str):
        self._refresh_btn.setEnabled(True)
        self._refresh_btn.setText("🔄 Actualizar")
        self._status_lbl.setText(f"Error al consultar Google Trends: {msg}")

    def refresh(self):
        """Called when switching to this tab."""
        # Auto-load if results are empty
        if self._results_layout.count() <= 1:
            self._start_fetch()
