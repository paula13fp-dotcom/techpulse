from __future__ import annotations
"""QApplication setup with global stylesheet."""
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont
from techpulse.ui.theme import QSS, FONT_FAMILY, FONT_SIZE_BASE


def create_app(argv: list[str] | None = None) -> QApplication:
    app = QApplication(argv or sys.argv)
    app.setApplicationName("TechPulse")
    app.setOrganizationName("TechPulse")
    app.setStyleSheet(QSS)
    font = QFont(FONT_FAMILY.split(",")[0].strip(), FONT_SIZE_BASE)
    app.setFont(font)
    return app
