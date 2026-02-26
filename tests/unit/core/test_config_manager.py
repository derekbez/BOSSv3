"""Tests for the config manager (load_config + save helpers)."""

import json
import os

import pytest

from boss.config.config_manager import load_config, save_system_location
from boss.core.models.config import BossConfig


class TestLoadConfig:
    def test_load_default_config(self):
        """The shipped boss_config.json should load without errors."""
        cfg = load_config()
        assert isinstance(cfg, BossConfig)
        assert cfg.system.webui_port == 8080

    def test_load_custom_config(self, tmp_path):
        config_file = tmp_path / "test_config.json"
        config_file.write_text(
            json.dumps(
                {
                    "hardware": {"screen_width": 800, "screen_height": 480},
                    "system": {"webui_port": 9090, "log_level": "DEBUG"},
                }
            )
        )
        cfg = load_config(config_file)
        assert cfg.hardware.screen_width == 800
        assert cfg.system.webui_port == 9090
        assert cfg.system.log_level == "DEBUG"

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_config(tmp_path / "nonexistent.json")

    def test_env_override_log_level(self, tmp_path, monkeypatch):
        config_file = tmp_path / "cfg.json"
        config_file.write_text(json.dumps({"hardware": {}, "system": {"log_level": "INFO"}}))
        monkeypatch.setenv("BOSS_LOG_LEVEL", "DEBUG")
        cfg = load_config(config_file)
        assert cfg.system.log_level == "DEBUG"

    def test_env_override_dev_mode(self, tmp_path, monkeypatch):
        config_file = tmp_path / "cfg.json"
        config_file.write_text(json.dumps({"hardware": {}, "system": {}}))
        monkeypatch.setenv("BOSS_DEV_MODE", "1")
        cfg = load_config(config_file)
        assert cfg.system.dev_mode is True

    def test_env_override_webui_port(self, tmp_path, monkeypatch):
        config_file = tmp_path / "cfg.json"
        config_file.write_text(json.dumps({"hardware": {}, "system": {}}))
        monkeypatch.setenv("BOSS_WEBUI_PORT", "3000")
        cfg = load_config(config_file)
        assert cfg.system.webui_port == 3000


class TestSaveSystemLocation:
    def test_save_location_updates_lat_lon(self, tmp_path):
        cfg_file = tmp_path / "cfg.json"
        cfg_file.write_text(
            json.dumps(
                {
                    "hardware": {},
                    "system": {
                        "location": {"lat": 1.0, "lon": 2.0},
                    },
                }
            )
        )

        updated = save_system_location(51.5, -0.12, cfg_file)

        assert updated.system.location.lat == pytest.approx(51.5)
        assert updated.system.location.lon == pytest.approx(-0.12)

        reloaded = load_config(cfg_file)
        assert reloaded.system.location.lat == pytest.approx(51.5)
        assert reloaded.system.location.lon == pytest.approx(-0.12)

    def test_save_location_preserves_other_fields(self, tmp_path):
        cfg_file = tmp_path / "cfg.json"
        cfg_file.write_text(
            json.dumps(
                {
                    "hardware": {"screen_width": 800},
                    "system": {
                        "webui_port": 9090,
                        "location": {"lat": 10.0, "lon": 20.0},
                    },
                }
            )
        )

        _ = save_system_location(11.0, 22.0, cfg_file)
        reloaded = load_config(cfg_file)

        assert reloaded.hardware.screen_width == 800
        assert reloaded.system.webui_port == 9090
        assert reloaded.system.location.lat == pytest.approx(11.0)
        assert reloaded.system.location.lon == pytest.approx(22.0)
