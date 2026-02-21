"""Tests for BossConfig, HardwareConfig, SystemConfig Pydantic models."""

import pytest
from pydantic import ValidationError

from boss.core.models.config import BossConfig, HardwareConfig, LocationConfig, SystemConfig


class TestHardwareConfig:
    def test_defaults(self):
        cfg = HardwareConfig()
        assert cfg.screen_width == 1024
        assert cfg.screen_height == 600
        assert cfg.audio_enabled is True
        assert cfg.go_button_pin == 0

    def test_custom_values(self):
        cfg = HardwareConfig(go_button_pin=17, screen_width=800)
        assert cfg.go_button_pin == 17
        assert cfg.screen_width == 800

    def test_extra_field_rejected(self):
        with pytest.raises(ValidationError, match="extra_field"):
            HardwareConfig(extra_field="boom")


class TestSystemConfig:
    def test_defaults(self):
        cfg = SystemConfig()
        assert cfg.log_level == "INFO"
        assert cfg.webui_port == 8080
        assert cfg.dev_mode is False
        assert cfg.test_mode is False
        assert cfg.event_bus_queue_size == 1000

    def test_location_default(self):
        cfg = SystemConfig()
        assert cfg.location.lat == pytest.approx(51.5074)
        assert cfg.location.lon == pytest.approx(-0.1278)

    def test_custom_location(self):
        cfg = SystemConfig(location=LocationConfig(lat=40.7, lon=-74.0))
        assert cfg.location.lat == pytest.approx(40.7)

    def test_extra_field_rejected(self):
        with pytest.raises(ValidationError):
            SystemConfig(nonexistent=True)


class TestBossConfig:
    def test_defaults(self):
        cfg = BossConfig()
        assert isinstance(cfg.hardware, HardwareConfig)
        assert isinstance(cfg.system, SystemConfig)

    def test_round_trip_json(self):
        cfg = BossConfig()
        raw = cfg.model_dump()
        cfg2 = BossConfig(**raw)
        assert cfg == cfg2

    def test_extra_top_level_rejected(self):
        with pytest.raises(ValidationError):
            BossConfig(unknown_section={})
