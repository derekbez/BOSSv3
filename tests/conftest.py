"""Shared pytest fixtures for BOSS v3 tests."""

from __future__ import annotations

import pytest

from boss.config.secrets_manager import SecretsManager
from boss.core.event_bus import EventBus
from boss.core.models.config import BossConfig


@pytest.fixture
async def event_bus():
    """Provide a started EventBus that is stopped after the test."""
    bus = EventBus(queue_size=100)
    await bus.start()
    yield bus
    await bus.stop()


@pytest.fixture(scope="session")
def boss_config() -> BossConfig:
    """Session-scoped default config (no file I/O)."""
    return BossConfig()


@pytest.fixture
def secrets() -> SecretsManager:
    """Fresh SecretsManager (no file loaded)."""
    return SecretsManager()
