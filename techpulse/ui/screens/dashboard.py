from __future__ import annotations
"""Dashboard screen: trending topics, product sentiment, daily digest."""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
    QFrame, QPushButton, QSizePolicy,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from techpulse.database.queries import (
    get_trending_topics, get_product_sentiment, get_latest_digest,
    get_post_count, get_source_stats,
)
from techpulse.ui.theme import COLORS
from techpulse.ui.widgets.sentiment_bar import SentimentBar


class _LoadWorker(QThread):
    done = pyqtSignal(dict)

    def run(self):
        data = {
            "trending": get_trending_topics(limit=8),
            "sentiment": get_product_sentiment(),
            "digest": get_latest_digest("daily"),
            "post_count": get_post_count(),
            "sources": get_source_stats(),
        }
        self.done.emit(data)


class DashboardScreen(QWidget):
    refresh_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(20)

        # Header
        header = QHBoxLayout()
        title = QLabel("Dashboard")
        title.setObjectName("title")
        header.addWidget(title)
        header.addStretch()

        self._status_label = QLabel("Cargando...")
        self._status_label.setObjectName("muted")
        header.addWidget(self._status_label)

        self._refresh_btn = QPushButton("⟳ Actualizar ahora")
        self._refresh_btn.clicked.connect(self.refresh_requested.emit)
        header.addWidget(self._refresh_btn)
        outer.addLayout(header)

        # Scroll area for the rest
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        self._content_layout = QVBoxLayout(content)
        self._content_layout.setSpacing(16)
        self._content_layout.setContentsMargins(0, 0, 0, 0)

        scroll.setWidget(content)
        outer.addWidget(scroll)

        # Placeholders
        self._stats_widget = QWidget()
        self._trending_widget = QWidget()
        self._sentiment_widget = QWidget()
        self._digest_widget = QWidget()

        for w in [self._stats_widget, self._trending_widget,
                  self._sentiment_widget, self._digest_widget]:
            self._content_layout.addWidget(w)

        self._content_layout.addStretch()

    def refresh(self):
        self._status_label.setText("Actualizando...")
        self._worker = _LoadWorker()
        self._worker.done.connect(self._on_data)
        self._worker.start()

    def _on_data(self, data: dict):
        self._rebuild_stats(data["post_count"], data["sources"])
        self._rebuild_trending(data["trending"])
        self._rebuild_sentiment(data["sentiment"])
        self._rebuild_digest(data["digest"])
        self._status_label.setText(
            f"{data['post_count']:,} posts indexados"
        )

    # ── Stats row ────────────────────────────────────────────
    def _rebuild_stats(self, post_count: int, sources: list[dict]):
        _clear_widget(self._stats_widget)
        layout = QHBoxLayout(self._stats_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        for label, value in [("Total posts", f"{post_count:,}")] + [
            (s["display_name"], str(s["post_count"])) for s in sources[:4]
        ]:
            card = _mini_stat(label, value)
            layout.addWidget(card)
        layout.addStretch()

    # ── Trending topics ──────────────────────────────────────
    def _rebuild_trending(self, topics: list[dict]):
        _clear_widget(self._trending_widget)
        layout = QVBoxLayout(self._trending_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        section = QLabel("🔥 TEMAS EN TENDENCIA")
        section.setObjectName("section")
        layout.addWidget(section)

        if not topics:
            layout.addWidget(QLabel("Sin datos aún. Realiza una actualización."))
            return

        for t in topics:
            card = QFrame()
            card.setObjectName("card")
            card_layout = QHBoxLayout(card)
            card_layout.setContentsMargins(12, 10, 12, 10)

            left = QVBoxLayout()
            label_lbl = QLabel(t.get("label", ""))
            label_lbl.setStyleSheet("font-weight: bold; font-size: 14px;")
            left.addWidget(label_lbl)

            desc = t.get("description", "")
            if desc:
                desc_lbl = QLabel(desc[:120])
                desc_lbl.setObjectName("muted")
                desc_lbl.setWordWrap(True)
                left.addWidget(desc_lbl)

            card_layout.addLayout(left, 1)

            right = QVBoxLayout()
            right.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            count_lbl = QLabel(f"{t.get('post_count', 0)} posts")
            count_lbl.setObjectName("muted")
            right.addWidget(count_lbl)
            if t.get("is_trending"):
                hot_lbl = QLabel("🔥 TRENDING")
                hot_lbl.setStyleSheet(
                    f"color: {COLORS['warning']}; font-size: 10px; font-weight: bold;"
                )
                right.addWidget(hot_lbl)
            card_layout.addLayout(right)
            layout.addWidget(card)

    # ── Product sentiment ────────────────────────────────────
    def _rebuild_sentiment(self, products: list[dict]):
        _clear_widget(self._sentiment_widget)
        layout = QVBoxLayout(self._sentiment_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        section = QLabel("📊 SENTIMIENTO POR PRODUCTO")
        section.setObjectName("section")
        layout.addWidget(section)

        if not products:
            layout.addWidget(QLabel("Sin análisis de sentimiento aún."))
            return

        for p in products[:8]:
            row = QFrame()
            row.setObjectName("card")
            row_layout = QVBoxLayout(row)
            row_layout.setContentsMargins(12, 8, 12, 8)
            row_layout.setSpacing(4)

            name_lbl = QLabel(p.get("canonical_name", ""))
            name_lbl.setStyleSheet("font-weight: 600; font-size: 13px;")
            row_layout.addWidget(name_lbl)

            bar = SentimentBar(
                positive=p.get("avg_positive", 0) / 100,
                neutral=p.get("avg_neutral", 0) / 100,
                negative=p.get("avg_negative", 0) / 100,
            )
            row_layout.addWidget(bar)
            layout.addWidget(row)

    # ── Daily digest ─────────────────────────────────────────
    def _rebuild_digest(self, digest: dict | None):
        _clear_widget(self._digest_widget)
        layout = QVBoxLayout(self._digest_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        section = QLabel("📰 RESUMEN DEL DÍA")
        section.setObjectName("section")
        layout.addWidget(section)

        if not digest:
            note = QLabel("El resumen diario se genera automáticamente a las 08:00.")
            note.setObjectName("muted")
            layout.addWidget(note)
            return

        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 12, 16, 12)

        date_lbl = QLabel(digest.get("generated_at", "")[:10])
        date_lbl.setObjectName("muted")
        card_layout.addWidget(date_lbl)

        content = QLabel(digest.get("content", "")[:1200])
        content.setWordWrap(True)
        content.setStyleSheet(f"color: {COLORS['text']}; line-height: 1.5;")
        card_layout.addWidget(content)
        layout.addWidget(card)


def _clear_widget(widget: QWidget):
    layout = widget.layout()
    if layout:
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        # Delete the layout itself (PyQt6-compatible)
        try:
            from PyQt6 import sip
            sip.delete(layout)
        except Exception:
            layout.deleteLater()


def _mini_stat(label: str, value: str) -> QFrame:
    card = QFrame()
    card.setObjectName("card")
    card.setFixedWidth(130)
    layout = QVBoxLayout(card)
    layout.setContentsMargins(12, 10, 12, 10)
    layout.setSpacing(2)
    val_lbl = QLabel(value)
    val_lbl.setStyleSheet("font-size: 22px; font-weight: bold; color: #E8EAF6;")
    lbl_lbl = QLabel(label)
    lbl_lbl.setObjectName("muted")
    layout.addWidget(val_lbl)
    layout.addWidget(lbl_lbl)
    return card
