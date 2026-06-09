"""
hotel_prediction.logger
=======================
Centralised logging configuration for the entire package.

Design
------
This module is **imported once** at the start of the Python process.
On first import it performs two side-effects that are intentional and
expected for a logging setup:

1. Creates the ``logs/`` directory if it does not exist.
2. Calls ``logging.basicConfig`` to attach a rotating file handler to
   the root logger (one log file per calendar day).

Every other module obtains a logger through :func:`get_logger`, which
returns a child of the root logger and attaches a console handler if
none is present yet.

Reusable
--------
get_logger : Return a named :class:`logging.Logger` with file + console output.

Example
-------
::

    from hotel_prediction.logger import get_logger

    logger = get_logger(__name__)
    logger.info("Hello from my_module")
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

__all__: list[str] = ["get_logger"]

# ── MODULE-LEVEL SETUP (runs once on import) ──────────────────────────────────

_LOGS_DIR: Path = Path("logs")
_LOGS_DIR.mkdir(exist_ok=True)

_LOG_FILE: Path = _LOGS_DIR / f"log_{datetime.now().strftime('%Y-%m-%d')}.log"

_LOG_FORMAT: str = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"

logging.basicConfig(
    filename=str(_LOG_FILE),
    format=_LOG_FORMAT,
    level=logging.INFO,
)

# Shared console handler — added to each named logger on first use.
_CONSOLE_HANDLER: logging.StreamHandler = logging.StreamHandler()
_CONSOLE_HANDLER.setLevel(logging.INFO)
_CONSOLE_HANDLER.setFormatter(logging.Formatter(_LOG_FORMAT))


# ── REUSABLE API ──────────────────────────────────────────────────────────────


def get_logger(name: str) -> logging.Logger:
    """Return a named logger configured with file and console output.

    The logger writes to both:
    - ``logs/log_YYYY-MM-DD.log`` (via the root basicConfig handler)
    - ``stderr`` (via the shared console handler)

    Args:
        name: Logger name — conventionally pass ``__name__`` so the
              logger hierarchy mirrors the module hierarchy.

    Returns:
        A :class:`logging.Logger` instance ready for use.

    Example:
        ::

            logger = get_logger(__name__)
            logger.info("Processing started")
            logger.warning("Something looks off")
            logger.error("Something went wrong")
    """
    logger: logging.Logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        logger.addHandler(_CONSOLE_HANDLER)
    return logger
