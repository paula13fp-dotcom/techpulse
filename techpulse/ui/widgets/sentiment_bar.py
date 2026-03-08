"""Horizontal sentiment bar: positive / neutral / negative."""
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QProgressBar
from PyQt6.QtCore import Qt
from techpulse.ui.theme import COLORS


class SentimentBar(QWidget):
    def __init__(self, positive: float = 0, neutral: float = 0, negative: float = 0, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        total = positive + neutral + negative or 1

        for pct, color, label in [
            (positive / total * 100, COLORS["positive"], f"✓ {positive:.0%}"),
            (neutral / total * 100, COLORS["neutral"], f"– {neutral:.0%}"),
            (negative / total * 100, COLORS["negative"], f"✗ {negative:.0%}"),
        ]:
            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(int(pct))
            bar.setTextVisible(False)
            bar.setFixedHeight(6)
            bar.setStyleSheet(f"""
                QProgressBar {{ background: {COLORS['surface2']}; border-radius: 3px; border: none; }}
                QProgressBar::chunk {{ background: {color}; border-radius: 3px; }}
            """)
            lbl = QLabel(label)
            lbl.setObjectName("muted")
            lbl.setFixedWidth(52)
            layout.addWidget(bar, int(pct) or 1)
            layout.addWidget(lbl)
