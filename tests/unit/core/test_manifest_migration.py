"""Tests for manifest migration enhancements (Phase 3)."""

from __future__ import annotations

import pytest
from boss.core.models.manifest import AppManifest, migrate_manifest_v2


class TestMigrateManifestV2:
    def test_strips_external_apis(self):
        raw = {
            "name": "test",
            "external_apis": ["ebird"],
            "timeout_behavior": "return",
        }
        result = migrate_manifest_v2(raw)
        assert "external_apis" not in result
        AppManifest(**result)  # should parse without error

    def test_maps_timeout_none(self):
        raw = {"name": "test", "timeout_behavior": "none"}
        result = migrate_manifest_v2(raw)
        assert result["timeout_behavior"] == "return"
        assert result["timeout_seconds"] == 900

    def test_maps_timeout_rerun(self):
        raw = {"name": "test", "timeout_behavior": "rerun", "timeout_seconds": 90}
        result = migrate_manifest_v2(raw)
        assert result["timeout_behavior"] == "return"
        assert result["timeout_seconds"] == 900

    def test_preserves_high_timeout(self):
        raw = {"name": "test", "timeout_behavior": "none", "timeout_seconds": 1200}
        result = migrate_manifest_v2(raw)
        assert result["timeout_seconds"] == 1200  # Already > 600, not overridden

    def test_return_behavior_unchanged(self):
        raw = {"name": "test", "timeout_behavior": "return", "timeout_seconds": 60}
        result = migrate_manifest_v2(raw)
        assert result["timeout_behavior"] == "return"
        assert result["timeout_seconds"] == 60

    def test_does_not_mutate_input(self):
        raw = {"name": "test", "external_apis": ["x"]}
        migrate_manifest_v2(raw)
        assert "external_apis" in raw  # Original untouched
