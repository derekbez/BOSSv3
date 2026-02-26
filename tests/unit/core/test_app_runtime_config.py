"""Tests for runtime app config overrides persistence."""

from __future__ import annotations

from boss.config.app_runtime_config import (
    clear_app_overrides,
    get_app_overrides,
    load_runtime_overrides,
    set_app_overrides,
)


class TestRuntimeOverrides:
    def test_load_missing_file_returns_empty(self, tmp_path):
        path = tmp_path / "missing.json"
        assert load_runtime_overrides(path) == {}

    def test_set_and_get_overrides(self, tmp_path):
        path = tmp_path / "overrides.json"

        set_app_overrides(
            "countdown_to_event",
            {
                "event_name": "Launch Day",
                "target_date": "2026-07-01",
                "target_time": "09:00:00",
                "refresh_seconds": 15.0,
            },
            path,
        )

        app_values = get_app_overrides("countdown_to_event", path)
        assert app_values["event_name"] == "Launch Day"
        assert app_values["refresh_seconds"] == 15.0

    def test_clear_overrides_removes_app(self, tmp_path):
        path = tmp_path / "overrides.json"
        set_app_overrides("countdown_to_event", {"event_name": "x"}, path)

        clear_app_overrides("countdown_to_event", path)

        assert get_app_overrides("countdown_to_event", path) == {}
        assert load_runtime_overrides(path) == {}
