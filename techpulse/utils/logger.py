"""Configured logger for all modules."""
import logging
import logging.handlers
from techpulse.config.settings import settings

settings.LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

_handler = logging.handlers.RotatingFileHandler(
    settings.LOG_PATH, maxBytes=5 * 1024 * 1024, backupCount=3
)
_handler.setFormatter(logging.Formatter(
    "%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
))

_console = logging.StreamHandler()
_console.setFormatter(logging.Formatter("%(levelname)-8s %(name)s: %(message)s"))

def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.addHandler(_handler)
        logger.addHandler(_console)
        logger.setLevel(logging.INFO)
    return logger
