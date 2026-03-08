from __future__ import annotations
"""PCComponents screen: trend radar — detects what the market is talking about
and whether PCComponents carries those products or not.

Features
--------
* Trend velocity      — week-on-week mention growth (↑↑ / → / ↓)
* Post snippet        — most-engaged post title per product
* Brand radar         — brand-level aggregated trends
* "New this week"     — badge for products with 0 prior-week mentions
* Source of demand    — per-platform mention breakdown
* Opportunity score   — 0-100 signal combining volume + velocity + sentiment
"""
import math

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
    QFrame, QPushButton, QSizePolicy,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtCore import QUrl

from techpulse.ui.theme import COLORS


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

_STOP_WORDS = {
    "de", "con", "para", "el", "la", "los", "las", "un", "una",
    "en", "y", "a", "del", "al", "por", "se", "su",
    "the", "with", "for", "and", "in", "of", "to",
}


def _is_catalog_match(query: str, product_name: str) -> bool:
    """Return True if a PCComponents result name actually matches the searched product."""
    q_tokens = {w.lower() for w in query.split() if len(w) > 2 and w.lower() not in _STOP_WORDS}
    p_tokens = {w.lower() for w in product_name.split() if len(w) > 2}
    if not q_tokens:
        return True
    matches = q_tokens & p_tokens
    return len(matches) >= 2 or (len(matches) / len(q_tokens)) >= 0.5


def _velocity_label(mentions_7d: int, mentions_prev_7d: int) -> tuple[str, str]:
    """Return (label_text, color) for the velocity indicator."""
    m7 = mentions_7d or 0
    mp7 = mentions_prev_7d or 0

    if mp7 == 0:
        if m7 > 0:
            return "🆕 Nuevo esta semana", COLORS["accent"]
        return "→ Sin datos recientes", COLORS["text_muted"]

    growth = (m7 - mp7) / mp7
    pct = int(growth * 100)

    if pct >= 200:
        return f"🚀 +{pct}% esta semana", "#ff4500"
    elif pct >= 50:
        return f"↑↑ +{pct}% esta semana", COLORS["accent"]
    elif pct >= 10:
        return f"↑ +{pct}% esta semana", COLORS["positive"]
    elif pct >= -10:
        return f"→ Estable ({pct:+d}%)", COLORS["text_muted"]
    else:
        return f"↓ {pct}% esta semana", COLORS["muted"]


def _calc_opportunity_score(
    mentions: int,
    mentions_7d: int,
    mentions_prev_7d: int,
    avg_positive: float | None,
    avg_negative: float | None,
    has_catalog_match: bool,
) -> int:
    """Calculate 0-100 opportunity score for a product gap."""
    score = 0

    # Volume contribution: 0-30 pts (logarithmic)
    volume_score = min(30, int(math.log2(max(mentions, 1)) * 4))
    score += volume_score

    # Velocity contribution: 0-30 pts
    m7 = mentions_7d or 0
    mp7 = mentions_prev_7d or 0
    if mp7 > 0:
        growth = (m7 - mp7) / mp7
        if growth > 2.0:
            score += 30
        elif growth > 1.0:
            score += 25
        elif growth > 0.5:
            score += 20
        elif growth > 0.2:
            score += 15
        elif growth > 0:
            score += 10
    elif m7 > 0:
        score += 25  # new this week is a strong positive signal

    # Sentiment contribution: 0-20 pts
    if avg_positive is not None:
        score += int((avg_positive or 0) * 20)
    else:
        score += 10  # neutral assumption

    # Not in catalog bonus: 0-20 pts
    if not has_catalog_match:
        score += 20

    return min(100, score)


def _score_color(score: int) -> str:
    if score >= 70:
        return COLORS["accent"]
    elif score >= 45:
        return COLORS["positive"]
    return COLORS["text_muted"]


# --------------------------------------------------------------------------- #
# Background workers
# --------------------------------------------------------------------------- #

class _TrendingProductsWorker(QThread):
    """Loads trending products from DB with enriched analytics data."""
    done = pyqtSignal(list)

    def run(self):
        from sqlalchemy import text
        from techpulse.database.connection import get_db

        with get_db() as conn:
            rows = conn.execute(text("""
                SELECT pr.id,
                       pr.canonical_name,
                       pr.brand,
                       dc.name AS category,
                       COUNT(ppm.id) AS mention_count,
                       SUM(CASE WHEN p.published_at >= datetime('now', '-7 days')
                                THEN 1 ELSE 0 END) AS mentions_7d,
                       SUM(CASE WHEN p.published_at >= datetime('now', '-14 days')
                                 AND p.published_at < datetime('now', '-7 days')
                                THEN 1 ELSE 0 END) AS mentions_prev_7d,
                       AVG(sr.positive_score) AS avg_positive,
                       AVG(sr.negative_score) AS avg_negative
                FROM products pr
                JOIN device_categories dc ON pr.category_id = dc.id
                JOIN post_product_mentions ppm ON ppm.product_id = pr.id
                JOIN posts p ON p.id = ppm.post_id
                LEFT JOIN sentiment_results sr ON sr.post_id = p.id
                WHERE pr.is_tracked = 1
                GROUP BY pr.id
                ORDER BY mention_count DESC
                LIMIT 20
            """)).fetchall()

            products = []
            for r in rows:
                d = dict(r._mapping)
                prod_id = d["id"]

                # Per-source breakdown (last 7 days)
                src_rows = conn.execute(text("""
                    SELECT s.display_name AS name, COUNT(*) AS cnt
                    FROM post_product_mentions ppm
                    JOIN posts p ON p.id = ppm.post_id
                    JOIN sources s ON s.id = p.source_id
                    WHERE ppm.product_id = :pid
                      AND p.published_at >= datetime('now', '-7 days')
                    GROUP BY s.id
                    ORDER BY cnt DESC
                    LIMIT 6
                """), {"pid": prod_id}).fetchall()
                d["sources"] = [{"name": row.name, "count": row.cnt} for row in src_rows]

                # Highest-engagement post snippet
                snip = conn.execute(text("""
                    SELECT p.title,
                           s.display_name AS src,
                           COALESCE(p.score, p.upvotes, p.like_count, 0) AS eng
                    FROM posts p
                    JOIN post_product_mentions ppm ON ppm.post_id = p.id
                    JOIN sources s ON s.id = p.source_id
                    WHERE ppm.product_id = :pid
                      AND p.title IS NOT NULL
                      AND p.title != ''
                    ORDER BY COALESCE(p.score, p.upvotes, p.like_count, 0) DESC
                    LIMIT 1
                """), {"pid": prod_id}).fetchone()
                d["top_post"] = dict(snip._mapping) if snip else None

                products.append(d)

        self.done.emit(products)


class _RadarWorker(QThread):
    """Searches each trending product and determines if PCComponents stocks it."""
    progress = pyqtSignal(str)
    result_ready = pyqtSignal(dict, object, bool)  # product_data, search_result, has_match
    done = pyqtSignal()

    def __init__(self, products: list[dict]):
        super().__init__()
        self.products = products

    def run(self):
        from techpulse.scrapers.pccomponents_scraper import search_product
        for p in self.products:
            name = p["canonical_name"]
            self.progress.emit(f"Analizando: {name}…")
            result = search_product(name)

            has_match = False
            if result.found:
                for prod in result.products[:3]:
                    if _is_catalog_match(name, prod.name):
                        has_match = True
                        break

            self.result_ready.emit(p, result, has_match)
        self.done.emit()


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


class _BrandRadarWidget(QFrame):
    """Brand-level aggregation widget built from trending product data."""

    def __init__(self, products: list[dict], parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)

        header = QLabel("🏷️  Brand Radar — tendencia por marcas (últimos 7 días)")
        header.setStyleSheet("font-size: 13px; font-weight: bold;")
        layout.addWidget(header)

        # Aggregate by brand
        brand_data: dict[str, dict] = {}
        for p in products:
            brand = (p.get("brand") or "Desconocido").strip() or "Desconocido"
            if brand not in brand_data:
                brand_data[brand] = {"mentions": 0, "mentions_7d": 0, "mentions_prev_7d": 0}
            brand_data[brand]["mentions"] += p.get("mention_count") or 0
            brand_data[brand]["mentions_7d"] += p.get("mentions_7d") or 0
            brand_data[brand]["mentions_prev_7d"] += p.get("mentions_prev_7d") or 0

        # Sort by last-7-days activity; show top 8
        sorted_brands = sorted(
            brand_data.items(),
            key=lambda x: x[1]["mentions_7d"],
            reverse=True,
        )[:8]

        if not sorted_brands:
            layout.addWidget(QLabel("Sin datos de marcas disponibles."))
            return

        max_m7 = max((b[1]["mentions_7d"] for b in sorted_brands), default=1) or 1

        for brand, data in sorted_brands:
            m7 = data["mentions_7d"]
            mp7 = data["mentions_prev_7d"]
            vel_text, vel_color = _velocity_label(m7, mp7)

            row = QHBoxLayout()

            brand_lbl = QLabel(brand)
            brand_lbl.setStyleSheet("font-size: 12px; font-weight: bold;")
            brand_lbl.setFixedWidth(110)
            row.addWidget(brand_lbl)

            # Mini bar chart
            bar_container = QWidget()
            bar_container.setFixedHeight(14)
            bar_container.setMinimumWidth(20)
            bar_container.setMaximumWidth(200)
            bar_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

            bar = QFrame(bar_container)
            bar_w = max(8, int((m7 / max_m7) * 180))
            bar.setGeometry(0, 1, bar_w, 12)
            bar.setStyleSheet(f"background: {COLORS['accent']}; border-radius: 3px;")

            row.addWidget(bar_container)
            row.addSpacing(8)

            count_lbl = QLabel(f"{m7} esta semana")
            count_lbl.setFixedWidth(110)
            count_lbl.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
            row.addWidget(count_lbl)

            vel_lbl = QLabel(vel_text)
            vel_lbl.setStyleSheet(f"color: {vel_color}; font-size: 11px;")
            row.addWidget(vel_lbl)

            row.addStretch()
            layout.addLayout(row)


def _make_source_row(sources: list[dict]) -> QLabel | None:
    """Build a compact source-breakdown label, or None if no data."""
    if not sources:
        return None
    parts = []
    for s in sources[:5]:
        name = s.get("name") or "?"
        cnt = s.get("count") or 0
        parts.append(f"📌 {name} ({cnt})")
    lbl = QLabel("  ".join(parts))
    lbl.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
    return lbl


def _make_snippet_widgets(top_post: dict | None) -> list[QLabel]:
    """Build post-snippet label(s) from top_post data."""
    if not top_post or not top_post.get("title"):
        return []
    title = top_post["title"]
    title_short = title[:120] + ("…" if len(title) > 120 else "")
    snip = QLabel(f"💬 \"{title_short}\"")
    snip.setWordWrap(True)
    snip.setStyleSheet("font-size: 11px; font-style: italic;")

    widgets = [snip]
    src = top_post.get("src")
    if src:
        attr = QLabel(f"— vía {src}")
        attr.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 10px;")
        widgets.append(attr)
    return widgets


class _GapCard(QFrame):
    """Product trending but NOT in PCComponents catalog → opportunity."""

    def __init__(self, product: dict, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(6)

        name = product["canonical_name"]
        mentions = product.get("mention_count") or 0
        m7 = product.get("mentions_7d") or 0
        mp7 = product.get("mentions_prev_7d") or 0
        avg_pos = product.get("avg_positive")
        avg_neg = product.get("avg_negative")
        sources = product.get("sources") or []
        top_post = product.get("top_post")
        is_new = (mp7 == 0 and m7 > 0)

        # ── Header ──────────────────────────────────────────────────────────
        header = QHBoxLayout()
        name_lbl = QLabel(name)
        name_lbl.setStyleSheet("font-size: 14px; font-weight: bold;")
        header.addWidget(name_lbl)
        header.addStretch()

        if is_new:
            badge = QLabel("🆕 NUEVO")
            badge.setStyleSheet(
                f"background: {COLORS['accent']}; color: white; font-size: 10px; "
                "font-weight: bold; border-radius: 4px; padding: 2px 6px;"
            )
            header.addWidget(badge)

        mention_lbl = QLabel(f"🔥 {mentions} menciones")
        mention_lbl.setStyleSheet(
            f"color: {COLORS['accent']}; font-size: 12px; font-weight: bold;"
        )
        header.addWidget(mention_lbl)
        layout.addLayout(header)

        # ── Score + velocity ─────────────────────────────────────────────────
        score = _calc_opportunity_score(mentions, m7, mp7, avg_pos, avg_neg, False)
        vel_text, vel_color = _velocity_label(m7, mp7)

        metrics_row = QHBoxLayout()
        score_lbl = QLabel(f"⭐ Oportunidad: {score}/100")
        score_lbl.setStyleSheet(
            f"color: {_score_color(score)}; font-size: 12px; font-weight: bold;"
        )
        metrics_row.addWidget(score_lbl)
        metrics_row.addStretch()

        vel_lbl = QLabel(vel_text)
        vel_lbl.setStyleSheet(f"color: {vel_color}; font-size: 12px;")
        metrics_row.addWidget(vel_lbl)
        layout.addLayout(metrics_row)

        # ── Catalog status ───────────────────────────────────────────────────
        status = QLabel("❌  No encontrado en catálogo PCComponents")
        status.setStyleSheet(f"color: {COLORS['negative']}; font-size: 12px;")
        layout.addWidget(status)

        # ── Source breakdown ─────────────────────────────────────────────────
        src_lbl = _make_source_row(sources)
        if src_lbl:
            layout.addWidget(src_lbl)

        # ── Top post snippet ─────────────────────────────────────────────────
        for w in _make_snippet_widgets(top_post):
            layout.addWidget(w)

        # ── Tip ─────────────────────────────────────────────────────────────
        tip = QLabel(
            "💡 Oportunidad: este producto tiene demanda en foros y redes "
            "pero no está disponible en PCComponents."
        )
        tip.setObjectName("muted")
        tip.setWordWrap(True)
        tip.setStyleSheet("font-size: 11px;")
        layout.addWidget(tip)


class _CatalogCard(QFrame):
    """Product trending AND found in PCComponents catalog."""

    def __init__(self, product: dict, result, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        name = product["canonical_name"]
        mentions = product.get("mention_count") or 0
        m7 = product.get("mentions_7d") or 0
        mp7 = product.get("mentions_prev_7d") or 0
        sources = product.get("sources") or []
        top_post = product.get("top_post")
        is_new = (mp7 == 0 and m7 > 0)

        # ── Header ──────────────────────────────────────────────────────────
        header = QHBoxLayout()
        name_lbl = QLabel(name)
        name_lbl.setStyleSheet("font-size: 14px; font-weight: bold;")
        header.addWidget(name_lbl)
        header.addStretch()

        if is_new:
            badge = QLabel("🆕 NUEVO")
            badge.setStyleSheet(
                f"background: {COLORS['accent']}; color: white; font-size: 10px; "
                "font-weight: bold; border-radius: 4px; padding: 2px 6px;"
            )
            header.addWidget(badge)

        mention_lbl = QLabel(f"🔥 {mentions} menciones")
        mention_lbl.setStyleSheet(
            f"color: {COLORS['accent']}; font-size: 12px; font-weight: bold;"
        )
        header.addWidget(mention_lbl)
        layout.addLayout(header)

        # ── Velocity ─────────────────────────────────────────────────────────
        vel_text, vel_color = _velocity_label(m7, mp7)
        vel_lbl = QLabel(vel_text)
        vel_lbl.setStyleSheet(f"color: {vel_color}; font-size: 12px;")
        layout.addWidget(vel_lbl)

        # ── Catalog status ───────────────────────────────────────────────────
        found_lbl = QLabel(f"✅  {result.total_hits} referencias en catálogo")
        found_lbl.setStyleSheet(f"color: {COLORS['positive']}; font-size: 12px;")
        layout.addWidget(found_lbl)

        # ── Source breakdown ─────────────────────────────────────────────────
        src_lbl = _make_source_row(sources)
        if src_lbl:
            layout.addWidget(src_lbl)

        # ── Top post snippet ─────────────────────────────────────────────────
        for w in _make_snippet_widgets(top_post):
            layout.addWidget(w)

        # ── Top 3 matching catalog results ───────────────────────────────────
        for p in result.products[:3]:
            if not _is_catalog_match(name, p.name):
                continue
            item = QFrame()
            item.setStyleSheet(
                f"background: {COLORS['surface2']}; border-radius: 8px; padding: 2px;"
            )
            row = QHBoxLayout(item)
            row.setContentsMargins(10, 6, 10, 6)

            left = QVBoxLayout()
            pname = QLabel(p.name[:80] + ("…" if len(p.name) > 80 else ""))
            pname.setStyleSheet("font-size: 11px;")
            left.addWidget(pname)

            stock_text = (
                p.stock_label if p.stock_label
                else ("En stock" if p.available else "Sin stock")
            )
            stock_color = COLORS["positive"] if p.available else COLORS["muted"]
            stock_lbl = QLabel(stock_text)
            stock_lbl.setStyleSheet(f"color: {stock_color}; font-size: 10px;")
            left.addWidget(stock_lbl)
            row.addLayout(left, 1)

            right = QVBoxLayout()
            right.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            price_lbl = QLabel(p.price)
            price_lbl.setStyleSheet(
                f"color: {COLORS['accent']}; font-weight: bold; font-size: 12px;"
            )
            right.addWidget(price_lbl)

            if p.url:
                btn = QPushButton("Ver →")
                btn.setObjectName("secondary")
                btn.setFixedWidth(60)
                btn.setFixedHeight(24)
                btn.clicked.connect(lambda _, u=p.url: QDesktopServices.openUrl(QUrl(u)))
                right.addWidget(btn)

            row.addLayout(right)
            layout.addWidget(item)


# --------------------------------------------------------------------------- #
# Main screen
# --------------------------------------------------------------------------- #

class PCComponentsScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._radar_worker = None
        self._trending_worker = None
        self._trending_products: list[dict] = []
        self._brand_radar_widget: _BrandRadarWidget | None = None
        self._build_ui()
        self._load_trending()

    def _build_ui(self):
        self._outer = QVBoxLayout(self)
        self._outer.setContentsMargins(24, 24, 24, 24)
        self._outer.setSpacing(16)

        # ── Title row ────────────────────────────────────────────────────────
        header = QHBoxLayout()
        title = QLabel("Radar de Tendencias")
        title.setObjectName("title")
        header.addWidget(title)
        header.addStretch()
        self._scan_btn = QPushButton("📡 Analizar tendencias")
        self._scan_btn.clicked.connect(self._start_radar)
        header.addWidget(self._scan_btn)
        self._outer.addLayout(header)

        desc = QLabel(
            "Detecta qué productos están generando conversación en Reddit, YouTube y foros "
            "y comprueba si PCComponents los tiene en catálogo. "
            "Los que no están son oportunidades de negocio."
        )
        desc.setObjectName("muted")
        desc.setWordWrap(True)
        self._outer.addWidget(desc)

        self._status_lbl = QLabel("")
        self._status_lbl.setObjectName("muted")
        self._outer.addWidget(self._status_lbl)

        # Brand radar placeholder (inserted dynamically after load)
        self._brand_radar_placeholder_idx = self._outer.count()

        # ── Scroll area for scan results ──────────────────────────────────────
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)

        self._results_widget = QWidget()
        self._results_layout = QVBoxLayout(self._results_widget)
        self._results_layout.setSpacing(10)
        self._results_layout.setContentsMargins(0, 0, 0, 0)
        self._results_layout.addStretch()

        self._scroll.setWidget(self._results_widget)
        self._outer.addWidget(self._scroll)

        # Internal state for two sections
        self._gap_section_added = False
        self._catalog_section_added = False
        self._gap_count = 0
        self._catalog_count = 0
        self._gap_insert_pos = 0
        self._catalog_insert_pos = 0

    # ── Data loading ─────────────────────────────────────────────────────────

    def _load_trending(self):
        self._status_lbl.setText("Cargando productos trending…")
        self._trending_worker = _TrendingProductsWorker()
        self._trending_worker.done.connect(self._on_trending)
        self._trending_worker.start()

    def _on_trending(self, products: list[dict]):
        self._trending_products = products

        # Refresh brand radar widget
        if self._brand_radar_widget is not None:
            self._outer.removeWidget(self._brand_radar_widget)
            self._brand_radar_widget.deleteLater()
            self._brand_radar_widget = None

        if products:
            self._brand_radar_widget = _BrandRadarWidget(products)
            # Insert just before the scroll area (second-to-last item)
            self._outer.insertWidget(self._brand_radar_placeholder_idx, self._brand_radar_widget)

            self._status_lbl.setText(
                f"{len(products)} productos detectados en los últimos scrapes. "
                f"Pulsa '📡 Analizar tendencias' para ver cuáles están en el catálogo de PCComponents."
            )
        else:
            self._status_lbl.setText(
                "No hay productos detectados aún. Realiza una actualización de datos primero."
            )

    # ── Radar scan ───────────────────────────────────────────────────────────

    def _start_radar(self):
        if not self._trending_products:
            self._status_lbl.setText("No hay productos detectados. Actualiza los datos primero.")
            return
        if self._radar_worker and self._radar_worker.isRunning():
            return

        # Clear previous results (keep the stretch at position 0)
        while self._results_layout.count() > 1:
            item = self._results_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._gap_section_added = False
        self._catalog_section_added = False
        self._gap_count = 0
        self._catalog_count = 0
        self._gap_insert_pos = 0
        self._catalog_insert_pos = 0

        self._scan_btn.setEnabled(False)
        self._scan_btn.setText("Analizando…")

        self._radar_worker = _RadarWorker(self._trending_products[:15])
        self._radar_worker.progress.connect(self._on_progress)
        self._radar_worker.result_ready.connect(self._on_result)
        self._radar_worker.done.connect(self._on_done)
        self._radar_worker.start()

    def _on_progress(self, msg: str):
        self._status_lbl.setText(msg)

    def _on_result(self, product: dict, result, has_match: bool):
        pos = max(0, self._results_layout.count() - 1)

        if not result.found or not has_match:
            # Trending but NOT in catalog → opportunity
            if not self._gap_section_added:
                hdr = _SectionHeader("🚨  Oportunidades de catálogo — trending pero NO disponible en PCComponents")
                self._results_layout.insertWidget(0, hdr)
                self._gap_section_added = True
                self._gap_insert_pos = 1
                pos = 1
            else:
                pos = self._gap_insert_pos

            card = _GapCard(product)
            self._results_layout.insertWidget(pos, card)
            self._gap_insert_pos = pos + 1
            self._gap_count += 1

        else:
            # Trending AND in catalog → confirm we sell it
            if not self._catalog_section_added:
                catalog_pos = self._gap_insert_pos if self._gap_section_added else 0
                hdr = _SectionHeader("📈  En catálogo — productos trending que PCComponents tiene")
                self._results_layout.insertWidget(catalog_pos, hdr)
                self._catalog_section_added = True
                self._catalog_insert_pos = catalog_pos + 1
                if self._gap_section_added:
                    self._gap_insert_pos += 1

            pos = self._catalog_insert_pos
            card = _CatalogCard(product, result)
            self._results_layout.insertWidget(pos, card)
            self._catalog_insert_pos = pos + 1
            self._catalog_count += 1

    def _on_done(self):
        self._scan_btn.setEnabled(True)
        self._scan_btn.setText("📡 Analizar tendencias")
        self._status_lbl.setText(
            f"Análisis completo — "
            f"🚨 {self._gap_count} oportunidades sin cubrir · "
            f"📈 {self._catalog_count} productos trending en catálogo"
        )

    def refresh(self):
        self._load_trending()
