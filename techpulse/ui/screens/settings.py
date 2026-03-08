"""Settings screen: API keys, scraping intervals, categories."""
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QComboBox, QScrollArea, QMessageBox,
)
from PyQt6.QtCore import pyqtSignal


class SettingsScreen(QWidget):
    settings_saved = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self._load_env()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(16)

        title = QLabel("Configuración")
        title.setObjectName("title")
        outer.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(20)
        layout.setContentsMargins(0, 0, 0, 0)

        # API Keys section
        layout.addWidget(self._section_label("🔑 API KEYS"))
        self._reddit_id = self._key_row(layout, "Reddit Client ID", "REDDIT_CLIENT_ID")
        self._reddit_secret = self._key_row(layout, "Reddit Client Secret", "REDDIT_CLIENT_SECRET", password=True)
        self._youtube_key = self._key_row(layout, "YouTube API Key", "YOUTUBE_API_KEY", password=True)
        self._anthropic_key = self._key_row(layout, "Anthropic API Key", "ANTHROPIC_API_KEY", password=True)

        layout.addWidget(self._separator())

        # Scraping settings
        layout.addWidget(self._section_label("⚙️ AJUSTES DE SCRAPING"))

        interval_row = QHBoxLayout()
        interval_row.addWidget(QLabel("Intervalo de actualización:"))
        self._interval_combo = QComboBox()
        self._interval_combo.addItems(["1 hora", "3 horas", "6 horas", "12 horas", "24 horas"])
        self._interval_combo.setCurrentIndex(2)  # 6h default
        interval_row.addWidget(self._interval_combo)
        interval_row.addStretch()
        layout.addLayout(interval_row)

        layout.addWidget(self._separator())

        # Save button
        save_btn = QPushButton("💾 Guardar configuración")
        save_btn.setFixedWidth(220)
        save_btn.clicked.connect(self._save)
        layout.addWidget(save_btn)

        # Instructions
        note = QLabel(
            "Las API keys se guardan en el archivo .env del proyecto. "
            "Reddit y YouTube requieren keys para funcionar. "
            "Los foros tech (XDA, GSMArena) funcionan sin configuración."
        )
        note.setObjectName("muted")
        note.setWordWrap(True)
        layout.addWidget(note)

        layout.addStretch()
        scroll.setWidget(content)
        outer.addWidget(scroll)

    def _section_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("section")
        return lbl

    def _separator(self) -> QFrame:
        sep = QFrame()
        sep.setObjectName("separator")
        sep.setFixedHeight(1)
        return sep

    def _key_row(self, layout: QVBoxLayout, label: str, env_key: str, password: bool = False) -> QLineEdit:
        row = QVBoxLayout()
        row.setSpacing(4)
        lbl = QLabel(label)
        lbl.setObjectName("muted")
        row.addWidget(lbl)
        field = QLineEdit()
        field.setPlaceholderText(f"Introduce tu {label}...")
        if password:
            field.setEchoMode(QLineEdit.EchoMode.Password)
        field.setProperty("env_key", env_key)
        row.addWidget(field)
        layout.addLayout(row)
        return field

    def _load_env(self):
        env_path = self._get_env_path()
        if not env_path.exists():
            return
        env_vals = {}
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                key, _, val = line.partition("=")
                env_vals[key.strip()] = val.strip()

        for field in [self._reddit_id, self._reddit_secret, self._youtube_key, self._anthropic_key]:
            key = field.property("env_key")
            if key in env_vals:
                field.setText(env_vals[key])

        interval_map = {"1": 0, "3": 1, "6": 2, "12": 3, "24": 4}
        hours = env_vals.get("SCRAPE_INTERVAL_HOURS", "6")
        self._interval_combo.setCurrentIndex(interval_map.get(hours, 2))

    def _save(self):
        interval_hours = ["1", "3", "6", "12", "24"][self._interval_combo.currentIndex()]
        lines = [
            f"REDDIT_CLIENT_ID={self._reddit_id.text().strip()}",
            f"REDDIT_CLIENT_SECRET={self._reddit_secret.text().strip()}",
            f"REDDIT_USER_AGENT=TechPulse/1.0",
            f"YOUTUBE_API_KEY={self._youtube_key.text().strip()}",
            f"ANTHROPIC_API_KEY={self._anthropic_key.text().strip()}",
            f"SCRAPE_INTERVAL_HOURS={interval_hours}",
            f"MAX_POSTS_PER_RUN=100",
        ]
        env_path = self._get_env_path()
        env_path.write_text("\n".join(lines) + "\n")

        QMessageBox.information(
            self, "Guardado",
            "Configuración guardada. Reinicia la aplicación para aplicar los cambios."
        )
        self.settings_saved.emit()

    def _get_env_path(self) -> Path:
        return Path(__file__).resolve().parents[4] / ".env"
