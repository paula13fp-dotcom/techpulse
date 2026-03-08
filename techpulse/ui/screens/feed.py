from __future__ import annotations
"""Feed screen: paginated list of posts with filters."""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
    QComboBox, QFrame, QPushButton, QSizePolicy,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from techpulse.database.queries import get_feed
from techpulse.ui.widgets.post_card import PostCard

PAGE_SIZE = 30

_ALL_SOURCES = "Todas las fuentes"
_ALL_CATS = "Todas las categorías"


def _load_source_names() -> list[str]:
    """Load source names from DB that actually have posts."""
    try:
        from techpulse.database.connection import get_db
        from sqlalchemy import text
        with get_db() as conn:
            rows = conn.execute(text("""
                SELECT s.name FROM sources s
                WHERE EXISTS (SELECT 1 FROM posts p WHERE p.source_id = s.id)
                ORDER BY s.name
            """)).fetchall()
        return [r.name for r in rows]
    except Exception:
        return ["reddit", "youtube", "xda", "gsmarena", "tiktok"]


class _FeedWorker(QThread):
    done = pyqtSignal(list)

    def __init__(self, source: str | None, category: str | None, offset: int):
        super().__init__()
        self.source = source
        self.category = category
        self.offset = offset

    def run(self):
        posts = get_feed(
            source_name=self.source,
            category_slug=self.category,
            limit=PAGE_SIZE,
            offset=self.offset,
        )
        self.done.emit(posts)


class FeedScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._offset = 0
        self._build_ui()
        self._load_posts()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(16)

        # Header
        header = QHBoxLayout()
        title = QLabel("Feed")
        title.setObjectName("title")
        header.addWidget(title)
        header.addStretch()
        outer.addLayout(header)

        # Filters
        filters = QHBoxLayout()
        filters.setSpacing(10)

        self._source_combo = QComboBox()
        self._source_combo.addItem(_ALL_SOURCES)
        self._source_combo.addItems(_load_source_names())
        self._source_combo.currentIndexChanged.connect(self._on_filter_change)

        self._cat_combo = QComboBox()
        self._cat_combo.addItems([_ALL_CATS, "phones", "smartwatches", "tablets"])
        self._cat_combo.currentIndexChanged.connect(self._on_filter_change)

        filters.addWidget(QLabel("Fuente:"))
        filters.addWidget(self._source_combo)
        filters.addWidget(QLabel("Categoría:"))
        filters.addWidget(self._cat_combo)
        filters.addStretch()
        outer.addLayout(filters)

        # Scroll area
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.verticalScrollBar().valueChanged.connect(self._on_scroll)

        self._list_widget = QWidget()
        self._list_layout = QVBoxLayout(self._list_widget)
        self._list_layout.setSpacing(8)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.addStretch()

        self._scroll.setWidget(self._list_widget)
        outer.addWidget(self._scroll)

        self._loading_label = QLabel("Cargando...")
        self._loading_label.setObjectName("muted")
        self._loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._loading_label.hide()
        outer.addWidget(self._loading_label)

    def _on_filter_change(self):
        self._offset = 0
        self._clear_list()
        self._load_posts()

    def _on_scroll(self, value: int):
        max_val = self._scroll.verticalScrollBar().maximum()
        if max_val > 0 and value >= max_val * 0.85:
            self._load_more()

    def _clear_list(self):
        while self._list_layout.count() > 1:  # Keep stretch
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _get_filters(self) -> tuple[str | None, str | None]:
        source = self._source_combo.currentText()
        source = None if source == _ALL_SOURCES else source
        cat = self._cat_combo.currentText()
        cat = None if cat == _ALL_CATS else cat
        return source, cat

    def _load_posts(self):
        self._loading_label.show()
        source, cat = self._get_filters()
        self._worker = _FeedWorker(source, cat, self._offset)
        self._worker.done.connect(self._on_posts)
        self._worker.start()

    def _load_more(self):
        if hasattr(self, "_worker") and self._worker.isRunning():
            return
        self._offset += PAGE_SIZE
        self._load_posts()

    def _on_posts(self, posts: list[dict]):
        self._loading_label.hide()
        # Insert before the stretch (last item)
        insert_pos = max(0, self._list_layout.count() - 1)
        for post in posts:
            card = PostCard(post)
            self._list_layout.insertWidget(insert_pos, card)
            insert_pos += 1

    def refresh(self):
        self._offset = 0
        self._clear_list()
        self._load_posts()
