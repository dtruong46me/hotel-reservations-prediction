import logging
import os
from datetime import datetime
from pathlib import Path

LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(exist_ok=True)

LOG_FILE = LOGS_DIR / f"log_{datetime.now().strftime('%Y-%m-%d')}.log"

logging.basicConfig(
    filename=str(LOG_FILE),
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    level=logging.INFO,
)

# Also output to console
_console_handler = logging.StreamHandler()
_console_handler.setLevel(logging.INFO)
_console_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
)


def get_logger(name: str) -> logging.Logger:
    """Return a module-level logger with both file and console handlers."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        logger.addHandler(_console_handler)
    return logger
