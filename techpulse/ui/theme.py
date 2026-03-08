"""Color palette, fonts, and QSS stylesheet."""

COLORS = {
    "bg": "#0F1117",
    "surface": "#1A1D27",
    "surface2": "#22263A",
    "border": "#2C3050",
    "accent": "#6C63FF",
    "accent_hover": "#8B83FF",
    "text": "#E8EAF6",
    "text_muted": "#9099B8",
    "positive": "#4CAF50",
    "negative": "#F44336",
    "neutral": "#9E9E9E",
    "warning": "#FF9800",
    "sidebar_bg": "#0A0C12",
    "sidebar_selected": "#1E2035",
}

FONT_FAMILY = "SF Pro Display, Helvetica Neue, Segoe UI, Arial"
FONT_SIZE_BASE = 13

QSS = f"""
QMainWindow, QWidget {{
    background-color: {COLORS['bg']};
    color: {COLORS['text']};
    font-family: {FONT_FAMILY};
    font-size: {FONT_SIZE_BASE}px;
}}

QScrollArea, QScrollArea > QWidget > QWidget {{
    background-color: transparent;
    border: none;
}}

QScrollBar:vertical {{
    background: {COLORS['surface']};
    width: 6px;
    border-radius: 3px;
}}
QScrollBar::handle:vertical {{
    background: {COLORS['border']};
    border-radius: 3px;
    min-height: 20px;
}}
QScrollBar::handle:vertical:hover {{
    background: {COLORS['accent']};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QPushButton {{
    background-color: {COLORS['accent']};
    color: white;
    border: none;
    border-radius: 8px;
    padding: 8px 16px;
    font-weight: bold;
    font-size: 13px;
}}
QPushButton:hover {{
    background-color: {COLORS['accent_hover']};
}}
QPushButton:pressed {{
    background-color: {COLORS['accent']};
    opacity: 0.8;
}}
QPushButton#secondary {{
    background-color: {COLORS['surface2']};
    color: {COLORS['text']};
    border: 1px solid {COLORS['border']};
}}
QPushButton#secondary:hover {{
    background-color: {COLORS['border']};
}}

QLineEdit, QTextEdit, QComboBox {{
    background-color: {COLORS['surface']};
    color: {COLORS['text']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    padding: 6px 10px;
    font-size: 13px;
}}
QLineEdit:focus, QTextEdit:focus {{
    border: 1px solid {COLORS['accent']};
}}

QComboBox::drop-down {{
    border: none;
    width: 24px;
}}
QComboBox QAbstractItemView {{
    background-color: {COLORS['surface2']};
    color: {COLORS['text']};
    border: 1px solid {COLORS['border']};
    selection-background-color: {COLORS['accent']};
    border-radius: 4px;
}}

QLabel {{
    color: {COLORS['text']};
    background: transparent;
}}
QLabel#muted {{
    color: {COLORS['text_muted']};
    font-size: 11px;
}}
QLabel#title {{
    font-size: 20px;
    font-weight: bold;
    color: {COLORS['text']};
}}
QLabel#section {{
    font-size: 11px;
    font-weight: bold;
    color: {COLORS['text_muted']};
    letter-spacing: 1px;
}}

QFrame#card {{
    background-color: {COLORS['surface']};
    border: 1px solid {COLORS['border']};
    border-radius: 12px;
    padding: 8px;
}}
QFrame#card:hover {{
    border: 1px solid {COLORS['accent']};
}}

QFrame#sidebar {{
    background-color: {COLORS['sidebar_bg']};
    border-right: 1px solid {COLORS['border']};
}}

QPushButton#nav_btn {{
    background-color: transparent;
    color: {COLORS['text_muted']};
    border: none;
    border-radius: 8px;
    padding: 10px 16px;
    text-align: left;
    font-size: 14px;
}}
QPushButton#nav_btn:hover {{
    background-color: {COLORS['sidebar_selected']};
    color: {COLORS['text']};
}}
QPushButton#nav_btn:checked {{
    background-color: {COLORS['sidebar_selected']};
    color: {COLORS['accent']};
    font-weight: bold;
}}

QFrame#separator {{
    background-color: {COLORS['border']};
    max-height: 1px;
}}

QProgressBar {{
    background-color: {COLORS['surface2']};
    border-radius: 4px;
    height: 8px;
    text-align: center;
    border: none;
}}
QProgressBar::chunk {{
    border-radius: 4px;
    background-color: {COLORS['accent']};
}}
"""
