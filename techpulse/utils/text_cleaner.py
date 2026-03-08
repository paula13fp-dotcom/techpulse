"""Text cleaning utilities."""
import re
from html.parser import HTMLParser


class _HTMLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.reset()
        self._fed: list[str] = []

    def handle_data(self, d: str):
        self._fed.append(d)

    def get_data(self) -> str:
        return " ".join(self._fed)


def strip_html(text: str) -> str:
    if not text:
        return ""
    s = _HTMLStripper()
    s.feed(text)
    return s.get_data()


def clean_text(text: str, max_length: int = 2000) -> str:
    if not text:
        return ""
    text = strip_html(text)
    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()
    # Remove non-printable characters
    text = "".join(c for c in text if c.isprintable() or c in "\n\t")
    return text[:max_length] if len(text) > max_length else text
