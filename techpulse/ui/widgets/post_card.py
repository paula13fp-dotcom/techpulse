"""Post card widget — shows a single post/video entry in the feed."""
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtCore import QUrl

from techpulse.ui.theme import COLORS

SOURCE_ICONS = {
    "reddit": "🟠",
    "youtube": "🔴",
    "tiktok": "⚫",
    "xda": "🟣",
    "gsmarena": "🔵",
}

SENTIMENT_COLORS = {
    "positive": COLORS["positive"],
    "negative": COLORS["negative"],
    "neutral": COLORS["neutral"],
    "mixed": COLORS["warning"],
}


class PostCard(QFrame):
    clicked = pyqtSignal(dict)

    def __init__(self, post_data: dict, parent=None):
        super().__init__(parent)
        self.post_data = post_data
        self.setObjectName("card")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(6)

        # Header: source icon + sentiment badge
        header = QHBoxLayout()
        header.setSpacing(8)

        source = self.post_data.get("source_name", "")
        icon = SOURCE_ICONS.get(source, "•")
        source_label = QLabel(f"{icon} {self.post_data.get('source_display', source).upper()}")
        source_label.setObjectName("section")
        header.addWidget(source_label)
        header.addStretch()

        sentiment = self.post_data.get("sentiment")
        if sentiment:
            badge = QLabel(sentiment.upper())
            color = SENTIMENT_COLORS.get(sentiment, COLORS["neutral"])
            badge.setStyleSheet(
                f"background: {color}22; color: {color}; border-radius: 4px; "
                f"padding: 2px 6px; font-size: 10px; font-weight: bold;"
            )
            header.addWidget(badge)

        layout.addLayout(header)

        # Title
        title = self.post_data.get("title") or self.post_data.get("body", "")[:120]
        if title:
            title_label = QLabel(title[:140])
            title_label.setWordWrap(True)
            title_label.setStyleSheet("font-size: 14px; font-weight: 600; color: #E8EAF6;")
            layout.addWidget(title_label)

        # Body snippet
        body = self.post_data.get("body", "")
        if body and body != title:
            snippet = body[:180].replace("\n", " ")
            body_label = QLabel(snippet + ("…" if len(body) > 180 else ""))
            body_label.setObjectName("muted")
            body_label.setWordWrap(True)
            layout.addWidget(body_label)

        # Footer: stats + date
        footer = QHBoxLayout()
        stats = self._build_stats()
        stats_label = QLabel(stats)
        stats_label.setObjectName("muted")
        footer.addWidget(stats_label)
        footer.addStretch()

        published = self.post_data.get("published_at", "")
        if published:
            date_label = QLabel(published[:10])
            date_label.setObjectName("muted")
            footer.addWidget(date_label)

        layout.addLayout(footer)

    def _build_stats(self) -> str:
        parts = []
        score = self.post_data.get("score", 0)
        comments = self.post_data.get("comment_count", 0)
        views = self.post_data.get("view_count", 0)
        if score:
            parts.append(f"↑ {score:,}")
        if comments:
            parts.append(f"💬 {comments:,}")
        if views:
            parts.append(f"👁 {self._fmt_num(views)}")
        return "  ".join(parts) if parts else ""

    def _fmt_num(self, n: int) -> str:
        if n >= 1_000_000:
            return f"{n/1_000_000:.1f}M"
        if n >= 1_000:
            return f"{n/1_000:.1f}K"
        return str(n)

    def mousePressEvent(self, event):
        url = self.post_data.get("url", "")
        if url:
            QDesktopServices.openUrl(QUrl(url))
        super().mousePressEvent(event)
