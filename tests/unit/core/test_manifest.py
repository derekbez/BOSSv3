"""Tests for AppManifest Pydantic model."""

import pytest
from pydantic import ValidationError

from boss.core.models.manifest import AppManifest, migrate_manifest_v2


class TestAppManifest:
    def test_minimal_valid(self):
        m = AppManifest(name="Test App")
        assert m.name == "Test App"
        assert m.entry_point == "main.py"
        assert m.timeout_seconds == 120
        assert m.config == {}
        assert m.required_env == []

    def test_config_field_preserved(self):
        """Regression: v2 silently dropped the config field."""
        m = AppManifest(name="Weather", config={"refresh_interval": 60, "units": "metric"})
        assert m.config["refresh_interval"] == 60
        assert m.config["units"] == "metric"

    def test_required_env(self):
        m = AppManifest(name="Weather", required_env=["OPENWEATHER_API_KEY"])
        assert m.required_env == ["OPENWEATHER_API_KEY"]

    def test_extra_field_rejected(self):
        with pytest.raises(ValidationError):
            AppManifest(name="Bad", surprise="boom")

    def test_timeout_must_be_positive(self):
        with pytest.raises(ValidationError):
            AppManifest(name="Bad", timeout_seconds=0)

    def test_defaults(self):
        m = AppManifest(name="X")
        assert m.version == "1.0.0"
        assert m.timeout_behavior == "return"
        assert m.requires_network is False
        assert m.tags == []

    def test_round_trip_json(self):
        m = AppManifest(name="Round", config={"k": [1, 2]})
        raw = m.model_dump()
        m2 = AppManifest(**raw)
        assert m == m2


class TestMigrateManifestV2:
    def test_no_changes_needed(self):
        raw = {"name": "App", "version": "1.0.0"}
        assert migrate_manifest_v2(raw) == raw

    def test_does_not_mutate_input(self):
        raw = {"name": "App"}
        result = migrate_manifest_v2(raw)
        assert result is not raw
