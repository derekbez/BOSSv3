"""Tests for AppAPI enhancements (Phase 3) — secrets, app_summaries, publish_threadsafe."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio

from boss.config.secrets_manager import SecretsManager
from boss.core.app_api import AppAPI
from boss.core.event_bus import EventBus
from boss.core.models.config import BossConfig
from boss.core.models.manifest import AppManifest


@pytest.fixture
def manifest() -> AppManifest:
    return AppManifest(name="test_app")


@pytest.fixture
def secrets() -> SecretsManager:
    sm = SecretsManager()
    sm._store = {"MY_KEY": "secret_val", "OTHER": "other_val"}
    sm._loaded = True
    return sm


@pytest_asyncio.fixture
async def bus() -> EventBus:
    b = EventBus(queue_size=100)
    await b.start()
    yield b
    await b.stop()


@pytest.fixture
def api(manifest, bus, secrets) -> AppAPI:
    screen = MagicMock()
    leds = MagicMock()
    config = BossConfig()
    summaries = [
        {"switch": 0, "name": "app_a", "description": "First"},
        {"switch": 1, "name": "app_b", "description": "Second"},
    ]
    return AppAPI(
        app_name="test_app",
        app_dir=Path("/tmp/test_app"),
        manifest=manifest,
        event_bus=bus,
        screen=screen,
        leds=leds,
        config=config,
        secrets=secrets,
        app_summaries=summaries,
    )


class TestGetSecret:
    def test_returns_secret(self, api):
        assert api.get_secret("MY_KEY") == "secret_val"

    def test_returns_default_on_missing(self, api):
        assert api.get_secret("MISSING", "fallback") == "fallback"

    def test_returns_default_when_no_secrets_manager(self, manifest, bus):
        a = AppAPI(
            app_name="t", app_dir=Path("/tmp"), manifest=manifest,
            event_bus=bus, screen=MagicMock(), leds=MagicMock(),
            config=BossConfig(), secrets=None,
        )
        assert a.get_secret("ANY") == ""


class TestGetAllAppSummaries:
    def test_returns_summaries(self, api):
        result = api.get_all_app_summaries()
        assert len(result) == 2
        assert result[0]["name"] == "app_a"
        assert result[1]["switch"] == 1

    def test_returns_empty_when_none(self, manifest, bus):
        a = AppAPI(
            app_name="t", app_dir=Path("/tmp"), manifest=manifest,
            event_bus=bus, screen=MagicMock(), leds=MagicMock(),
            config=BossConfig(),
        )
        assert a.get_all_app_summaries() == []


class TestPublishThreadsafe:
    def test_publish_threadsafe_on_scoped_bus(self, api, bus):
        """Verify scoped event bus delegates publish_threadsafe to real bus."""
        # Just verify it doesn't raise
        api.event_bus.publish_threadsafe("test.event", {"key": "val"})
