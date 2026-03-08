from __future__ import annotations
"""Main application window with sidebar navigation."""
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QLabel, QFrame, QStackedWidget,
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject
from PyQt6.QtGui import QFont

from techpulse.ui.theme import COLORS
from techpulse.ui.screens.dashboard import DashboardScreen
from techpulse.ui.screens.feed import FeedScreen
from techpulse.ui.screens.pccomponents import PCComponentsScreen
from techpulse.ui.screens.google_trends import GoogleTrendsScreen
from techpulse.ui.screens.settings import SettingsScreen
from techpulse.scheduler.job_manager import trigger_now, set_scrape_done_callback, get_next_run


class _Bridge(QObject):
    """Thread-safe bridge: emits signals on the main thread from background threads."""
    scrape_done = pyqtSignal()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TechPulse")
        self.setMinimumSize(1100, 700)
        self.resize(1280, 800)
        self._bridge = _Bridge()
        self._bridge.scrape_done.connect(self._on_scrape_done)
        self._build_ui()
        self._setup_scheduler_callback()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        sidebar = self._build_sidebar()
        main_layout.addWidget(sidebar)

        self._stack = QStackedWidget()
        self._dashboard = DashboardScreen()
        self._feed = FeedScreen()
        self._pccomponents = PCComponentsScreen()
        self._google_trends = GoogleTrendsScreen()
        self._settings = SettingsScreen()

        self._stack.addWidget(self._dashboard)       # index 0
        self._stack.addWidget(self._feed)            # index 1
        self._stack.addWidget(self._pccomponents)    # index 2
        self._stack.addWidget(self._google_trends)   # index 3
        self._stack.addWidget(self._settings)        # index 4
        main_layout.addWidget(self._stack, 1)

        self._dashboard.refresh_requested.connect(self._manual_refresh)

    def _build_sidebar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(200)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(12, 24, 12, 24)
        layout.setSpacing(4)

        logo = QLabel("TechPulse")
        logo.setStyleSheet(
            f"font-size: 18px; font-weight: bold; color: {COLORS['accent']}; "
            f"padding: 8px 8px 16px 8px;"
        )
        layout.addWidget(logo)

        self._nav_buttons = []
        nav_items = [
            ("🏠  Dashboard", 0),
            ("📰  Feed", 1),
            ("🛒  PCComponents", 2),
            ("📊  Google Trends", 3),
            ("⚙️  Configuración", 4),
        ]

        for label, idx in nav_items:
            btn = QPushButton(label)
            btn.setObjectName("nav_btn")
            btn.setCheckable(True)
            btn.setChecked(idx == 0)
            btn.clicked.connect(lambda checked, i=idx: self._navigate(i))
            layout.addWidget(btn)
            self._nav_buttons.append(btn)

        layout.addStretch()

        self._next_run_label = QLabel("")
        self._next_run_label.setObjectName("muted")
        self._next_run_label.setWordWrap(True)
        self._next_run_label.setStyleSheet("font-size: 10px; padding: 4px 8px;")
        layout.addWidget(self._next_run_label)

        return sidebar

    def _navigate(self, index: int):
        for i, btn in enumerate(self._nav_buttons):
            btn.setChecked(i == index)
        self._stack.setCurrentIndex(index)
        if index == 1:
            self._feed.refresh()
        elif index == 2:
            self._pccomponents.refresh()
        elif index == 3:
            self._google_trends.refresh()

    def _manual_refresh(self):
        trigger_now()

    def _setup_scheduler_callback(self):
        # Called from background thread — emit signal to cross to main thread safely
        set_scrape_done_callback(self._bridge.scrape_done.emit)

    def _on_scrape_done(self):
        """Runs on the main Qt thread after every scrape cycle."""
        self._dashboard.refresh()
        self._feed.refresh()
        next_run = get_next_run()
        if next_run:
            self._next_run_label.setText(f"Próxima sync:\n{next_run[11:16]}")
