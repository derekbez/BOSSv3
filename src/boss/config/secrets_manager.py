"""Thread-safe secrets manager with lazy file loading.

Precedence: ``os.environ`` → secrets file → caller-supplied default.

The secrets file is located by checking (in order):
1. ``BOSS_SECRETS_FILE`` environment variable
2. ``secrets/secrets.env`` (project root)
3. ``/etc/boss/secrets.env`` (system-wide)

File format: ``KEY=VALUE`` lines.  ``#`` comments and blank lines are
ignored.  Surrounding quotes on values are stripped.
"""

from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Any

import logging as _logging

_log = _logging.getLogger(__name__)

# Candidate paths, evaluated in order.
_DEFAULT_PATHS: list[str] = [
    "secrets/secrets.env",
    "/etc/boss/secrets.env",
]


class SecretsManager:
    """Thread-safe, lazy-loaded secrets store."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._loaded = False
        self._store: dict[str, str] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, key: str, default: str = "") -> str:
        """Return the value for *key*.

        Resolution order: process env → secrets file → *default*.
        """
        # Fast path – real env var always wins.
        env_val = os.environ.get(key)
        if env_val is not None:
            return env_val

        self._ensure_loaded()
        return self._store.get(key, default)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        with self._lock:
            if self._loaded:  # double-checked locking
                return
            self._load()
            self._loaded = True

    def _load(self) -> None:
        path = self._resolve_path()
        if path is None:
            _log.debug("No secrets file found — only os.environ will be used")
            return

        _log.info("Loading secrets from %s", path)
        self._store = self._parse_env_file(path)

    @staticmethod
    def _resolve_path() -> Path | None:
        """Return the first existing secrets file, or ``None``."""
        explicit = os.environ.get("BOSS_SECRETS_FILE")
        if explicit:
            p = Path(explicit)
            if p.is_file():
                return p
            _log.warning("BOSS_SECRETS_FILE=%s does not exist", explicit)
            return None

        for candidate in _DEFAULT_PATHS:
            p = Path(candidate)
            if p.is_file():
                return p
        return None

    @staticmethod
    def _parse_env_file(path: Path) -> dict[str, str]:
        """Parse a simple ``KEY=VALUE`` env file."""
        store: dict[str, str] = {}
        for lineno, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                _log.warning("Ignoring malformed line %d in %s", lineno, path)
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip("\"'")
            store[key] = value
        return store
