"""Logging setup, contextual logger, and rotating file handler."""

from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from typing import Any


# ---------------------------------------------------------------------------
# Format
# ---------------------------------------------------------------------------
_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


# ---------------------------------------------------------------------------
# setup_logging
# ---------------------------------------------------------------------------
def setup_logging(
    log_level: str = "INFO",
    log_dir: str = "logs",
    max_bytes: int = 5 * 1024 * 1024,  # 5 MB
    backup_count: int = 3,
) -> None:
    """Configure the root logger with console + rotating-file handlers.

    Safe to call multiple times – existing handlers are cleared first.

    Args:
        log_level: One of DEBUG / INFO / WARNING / ERROR / CRITICAL.
        log_dir: Directory for log files (created if absent).
        max_bytes: Max size per log file before rotation.
        backup_count: Number of rotated backup files to keep.
    """
    level = getattr(logging, log_level.upper(), logging.INFO)

    root = logging.getLogger()
    root.setLevel(level)

    # Remove any previously-installed handlers (idempotent re-init).
    for handler in root.handlers[:]:
        root.removeHandler(handler)
        handler.close()

    formatter = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)

    # Console handler
    console = logging.StreamHandler()
    console.setLevel(level)
    console.setFormatter(formatter)
    root.addHandler(console)

    # Rotating file handler
    os.makedirs(log_dir, exist_ok=True)
    file_path = os.path.join(log_dir, "boss.log")
    file_handler = RotatingFileHandler(
        file_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)


# ---------------------------------------------------------------------------
# get_logger
# ---------------------------------------------------------------------------
def get_logger(name: str) -> logging.Logger:
    """Return a stdlib Logger for *name* (typically ``__name__``)."""
    return logging.getLogger(name)


# ---------------------------------------------------------------------------
# ContextualLogger
# ---------------------------------------------------------------------------
class ContextualLogger:
    """Thin wrapper that prepends ``[key=value …]`` context to every message.

    Usage::

        log = ContextualLogger(get_logger(__name__), app="weather", switch=42)
        log.info("Fetching data")  # => "[app=weather switch=42] Fetching data"
    """

    def __init__(self, logger: logging.Logger, **context: Any) -> None:
        self._logger = logger
        self._prefix = " ".join(f"[{k}={v}]" for k, v in context.items())

    # -- convenience shortcuts -----------------------------------------------

    def _fmt(self, msg: str) -> str:
        return f"{self._prefix} {msg}" if self._prefix else msg

    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._logger.debug(self._fmt(msg), *args, **kwargs)

    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._logger.info(self._fmt(msg), *args, **kwargs)

    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._logger.warning(self._fmt(msg), *args, **kwargs)

    def error(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._logger.error(self._fmt(msg), *args, **kwargs)

    def critical(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._logger.critical(self._fmt(msg), *args, **kwargs)

    def exception(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._logger.exception(self._fmt(msg), *args, **kwargs)
