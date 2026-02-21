"""Tests for the AppManager."""

import json

import pytest

from boss.config.secrets_manager import SecretsManager
from boss.core.app_manager import AppManager
from tests.helpers.app_scaffold import create_app


@pytest.fixture
def apps_dir(tmp_path):
    return tmp_path / "apps"


@pytest.fixture
def mappings_path(tmp_path):
    return tmp_path / "app_mappings.json"


@pytest.fixture
def secrets():
    return SecretsManager()


class TestAppManager:
    def test_scan_discovers_apps(self, apps_dir, mappings_path, secrets):
        create_app(apps_dir, "hello")
        create_app(apps_dir, "weather")
        mappings_path.write_text(json.dumps({"1": "hello", "2": "weather"}))

        mgr = AppManager(apps_dir, mappings_path, secrets)
        result = mgr.scan_apps()

        assert "hello" in result
        assert "weather" in result

    def test_get_app_for_switch(self, apps_dir, mappings_path, secrets):
        create_app(apps_dir, "jokes")
        mappings_path.write_text(json.dumps({"42": "jokes"}))

        mgr = AppManager(apps_dir, mappings_path, secrets)
        mgr.scan_apps()

        assert mgr.get_app_for_switch(42) == "jokes"
        assert mgr.get_app_for_switch(99) is None

    def test_invalid_manifest_skipped(self, apps_dir, mappings_path, secrets):
        # Create a valid app
        create_app(apps_dir, "good")
        # Create a broken app (invalid JSON manifest)
        bad_dir = apps_dir / "bad"
        bad_dir.mkdir(parents=True)
        (bad_dir / "manifest.json").write_text("{invalid json", encoding="utf-8")
        (bad_dir / "main.py").write_text("def run(s,a): pass")

        mappings_path.write_text(json.dumps({"1": "good"}))

        mgr = AppManager(apps_dir, mappings_path, secrets)
        result = mgr.scan_apps()

        assert "good" in result
        assert "bad" not in result

    def test_mapping_to_missing_app_skipped(self, apps_dir, mappings_path, secrets):
        create_app(apps_dir, "real")
        mappings_path.write_text(json.dumps({"1": "real", "2": "ghost"}))

        mgr = AppManager(apps_dir, mappings_path, secrets)
        mgr.scan_apps()

        assert mgr.get_app_for_switch(1) == "real"
        assert mgr.get_app_for_switch(2) is None

    def test_required_env_warning(self, apps_dir, mappings_path, secrets, caplog):
        create_app(
            apps_dir,
            "needs_key",
            manifest_overrides={"required_env": ["MISSING_KEY"]},
        )
        mappings_path.write_text(json.dumps({}))

        mgr = AppManager(apps_dir, mappings_path, secrets)
        mgr.scan_apps()

        assert "MISSING_KEY" in caplog.text

    def test_no_apps_dir(self, tmp_path, mappings_path, secrets):
        mgr = AppManager(tmp_path / "nonexistent", mappings_path, secrets)
        result = mgr.scan_apps()
        assert result == {}

    def test_get_manifest(self, apps_dir, mappings_path, secrets):
        create_app(apps_dir, "myapp")
        mappings_path.write_text(json.dumps({}))

        mgr = AppManager(apps_dir, mappings_path, secrets)
        mgr.scan_apps()

        m = mgr.get_manifest("myapp")
        assert m is not None
        assert m.name == "Myapp"

    def test_get_app_dir(self, apps_dir, mappings_path, secrets):
        create_app(apps_dir, "myapp")
        mappings_path.write_text(json.dumps({}))

        mgr = AppManager(apps_dir, mappings_path, secrets)
        mgr.scan_apps()

        assert mgr.get_app_dir("myapp") == apps_dir / "myapp"
        assert mgr.get_app_dir("nonexistent") is None
