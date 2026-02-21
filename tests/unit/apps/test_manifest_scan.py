"""Manifest scan — verify every app directory has a valid manifest.json."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from boss.core.models.manifest import AppManifest, migrate_manifest_v2

APPS_DIR = Path(__file__).resolve().parents[3] / "src" / "boss" / "apps"


def _discover_apps() -> list[Path]:
    """Return all app directories (excluding _lib and __pycache__)."""
    return sorted(
        d
        for d in APPS_DIR.iterdir()
        if d.is_dir()
        and not d.name.startswith("_")
        and not d.name.startswith("__")
    )


@pytest.fixture(params=_discover_apps(), ids=lambda p: p.name)
def app_dir(request: pytest.FixtureRequest) -> Path:
    return request.param


class TestManifestScan:
    def test_manifest_exists(self, app_dir: Path):
        manifest_path = app_dir / "manifest.json"
        assert manifest_path.exists(), f"{app_dir.name} missing manifest.json"

    def test_manifest_valid_json(self, app_dir: Path):
        manifest_path = app_dir / "manifest.json"
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert isinstance(raw, dict)

    def test_manifest_parses(self, app_dir: Path):
        manifest_path = app_dir / "manifest.json"
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
        migrated = migrate_manifest_v2(raw)
        manifest = AppManifest(**migrated)
        assert manifest.name == app_dir.name

    def test_entry_point_exists(self, app_dir: Path):
        manifest_path = app_dir / "manifest.json"
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
        entry = raw.get("entry_point", "main.py")
        assert (app_dir / entry).exists(), f"{app_dir.name}/{entry} missing"

    def test_entry_point_defines_run(self, app_dir: Path):
        manifest_path = app_dir / "manifest.json"
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
        entry = raw.get("entry_point", "main.py")
        source = (app_dir / entry).read_text(encoding="utf-8")
        assert "def run(" in source, f"{app_dir.name}/{entry} missing run() function"
