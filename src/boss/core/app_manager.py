"""App manager — discovers mini-apps, loads manifests, binds switch mappings."""

from __future__ import annotations

import json
import logging as _logging
from pathlib import Path
from typing import Any

from boss.config.secrets_manager import SecretsManager
from boss.core.models.manifest import AppManifest, migrate_manifest_v2

_log = _logging.getLogger(__name__)


class AppManager:
    """Scans the ``apps/`` directory tree, validates manifests, and resolves
    switch-value → app-name via ``app_mappings.json``.

    Args:
        apps_dir: Absolute path to the ``apps/`` directory.
        mappings_path: Absolute path to ``app_mappings.json``.
        secrets: A :class:`SecretsManager` used to validate ``required_env``.
    """

    def __init__(
        self,
        apps_dir: Path,
        mappings_path: Path,
        secrets: SecretsManager,
    ) -> None:
        self._apps_dir = apps_dir
        self._mappings_path = mappings_path
        self._secrets = secrets

        # app_name → AppManifest
        self._manifests: dict[str, AppManifest] = {}
        # switch_value (str for JSON compat) → app_name
        self._switch_map: dict[int, str] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def scan_apps(self) -> dict[str, AppManifest]:
        """Discover apps, load manifests, bind mappings.  Returns all manifests.

        Call this once at startup after constructing the manager.
        """
        self._manifests = self._load_manifests()
        self._switch_map = self._load_mappings()
        self._validate_required_env()
        _log.info(
            "App scan complete: %d apps discovered, %d switch mappings loaded",
            len(self._manifests),
            len(self._switch_map),
        )
        return dict(self._manifests)

    def get_app_for_switch(self, value: int) -> str | None:
        """Return the app name mapped to *value*, or ``None``."""
        return self._switch_map.get(value)

    def get_manifest(self, app_name: str) -> AppManifest | None:
        """Return the manifest for *app_name*, or ``None`` if unknown."""
        return self._manifests.get(app_name)

    def get_all_manifests(self) -> dict[str, AppManifest]:
        """Return a copy of all discovered manifests."""
        return dict(self._manifests)

    def get_app_dir(self, app_name: str) -> Path | None:
        """Return the directory for *app_name*, or ``None``."""
        d = self._apps_dir / app_name
        return d if d.is_dir() else None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_manifests(self) -> dict[str, AppManifest]:
        manifests: dict[str, AppManifest] = {}
        if not self._apps_dir.is_dir():
            _log.warning("Apps directory does not exist: %s", self._apps_dir)
            return manifests

        for child in sorted(self._apps_dir.iterdir()):
            if not child.is_dir():
                continue
            manifest_path = child / "manifest.json"
            if not manifest_path.is_file():
                _log.debug("Skipping %s (no manifest.json)", child.name)
                continue
            try:
                raw = json.loads(manifest_path.read_text(encoding="utf-8"))
                raw = migrate_manifest_v2(raw)
                manifest = AppManifest(**raw)
                manifests[child.name] = manifest
                _log.debug("Loaded manifest for %s", child.name)
            except Exception:
                _log.exception("Invalid manifest in %s — skipping", child.name)

        return manifests

    def _load_mappings(self) -> dict[int, str]:
        if not self._mappings_path.is_file():
            _log.warning("Mappings file not found: %s", self._mappings_path)
            return {}
        raw: dict[str, str] = json.loads(
            self._mappings_path.read_text(encoding="utf-8")
        )
        switch_map: dict[int, str] = {}
        for key, app_name in raw.items():
            try:
                switch_val = int(key)
            except ValueError:
                _log.warning("Non-integer switch key %r in mappings — skipping", key)
                continue
            if app_name not in self._manifests:
                _log.warning(
                    "Mapping %d → %s but app not found in apps/ — skipping",
                    switch_val,
                    app_name,
                )
                continue
            switch_map[switch_val] = app_name
        return switch_map

    def _validate_required_env(self) -> None:
        """Warn at startup if any app's ``required_env`` keys are missing."""
        for app_name, manifest in self._manifests.items():
            for env_key in manifest.required_env:
                if not self._secrets.get(env_key):
                    _log.warning(
                        "App '%s' requires env/secret '%s' but it is not set",
                        app_name,
                        env_key,
                    )
