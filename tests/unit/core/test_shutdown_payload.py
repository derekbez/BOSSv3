"""Tests for admin_shutdown → SystemManager payload alignment (Bug #1).

Ensures the admin_shutdown app sends payloads with both ``action`` and
``reason`` keys, and that SystemManager dispatches the correct action
for each.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from boss.config.secrets_manager import SecretsManager
from boss.core.event_bus import EventBus
from boss.core.models.config import BossConfig
from boss.core.models.event import Event
from boss.core.system_manager import SystemManager


@pytest.fixture
def system_manager(tmp_path: Path):
    """Create a SystemManager with minimal config for testing."""
    config = BossConfig()
    bus = MagicMock(spec=EventBus)
    bus.start = AsyncMock()
    bus.stop = AsyncMock()
    bus.publish = AsyncMock()
    bus.subscribe = MagicMock()
    factory = MagicMock()
    factory.create_buttons.return_value = MagicMock()
    factory.create_go_button.return_value = MagicMock()
    factory.create_leds.return_value = MagicMock()
    factory.create_switches.return_value = MagicMock()
    factory.create_switches.return_value.get_value.return_value = 0
    factory.create_display.return_value = MagicMock()
    factory.create_screen.return_value = MagicMock()
    secrets = SecretsManager()

    apps_dir = tmp_path / "apps"
    apps_dir.mkdir()
    mappings = tmp_path / "app_mappings.json"
    mappings.write_text('{"app_mappings": {}, "parameters": {}}')

    return SystemManager(
        config=config,
        event_bus=bus,
        hardware_factory=factory,
        apps_dir=apps_dir,
        mappings_path=mappings,
        secrets=secrets,
    )


class TestShutdownPayloadAlignment:
    """Verify SystemManager correctly handles the payloads admin_shutdown sends."""

    @pytest.mark.asyncio
    async def test_reboot_payload_triggers_reboot(self, system_manager: SystemManager) -> None:
        """The payload admin_shutdown sends for reboot must trigger 'sudo reboot'."""
        system_manager._config.system.dev_mode = False
        # This is the exact payload admin_shutdown now sends:
        event = Event(
            event_type="system.shutdown.requested",
            payload={"action": "reboot", "reason": "reboot"},
        )

        with patch("boss.core.system_manager.subprocess.Popen") as mock_popen:
            await system_manager._on_shutdown_requested(event)
            mock_popen.assert_called_once_with(["sudo", "reboot"])

    @pytest.mark.asyncio
    async def test_poweroff_payload_triggers_shutdown(self, system_manager: SystemManager) -> None:
        """The payload admin_shutdown sends for poweroff must trigger 'sudo shutdown'."""
        system_manager._config.system.dev_mode = False
        # This is the exact payload admin_shutdown now sends:
        event = Event(
            event_type="system.shutdown.requested",
            payload={"action": "shutdown", "reason": "poweroff"},
        )

        with patch("boss.core.system_manager.subprocess.Popen") as mock_popen:
            await system_manager._on_shutdown_requested(event)
            mock_popen.assert_called_once_with(["sudo", "shutdown", "-h", "now"])

    @pytest.mark.asyncio
    async def test_exit_payload_triggers_sys_exit(self, system_manager: SystemManager) -> None:
        """The payload admin_shutdown sends for exit must call sys.exit(0)."""
        # This is the exact payload admin_shutdown now sends:
        event = Event(
            event_type="system.shutdown.requested",
            payload={"action": "exit", "reason": "exit_to_os"},
        )

        with patch("boss.core.system_manager.sys.exit") as mock_exit:
            await system_manager._on_shutdown_requested(event)
            mock_exit.assert_called_once_with(0)

    @pytest.mark.asyncio
    async def test_missing_action_defaults_to_exit(self, system_manager: SystemManager) -> None:
        """If action is missing, should default to exit (backward compat)."""
        event = Event(
            event_type="system.shutdown.requested",
            payload={"reason": "unknown"},
        )

        with patch("boss.core.system_manager.sys.exit") as mock_exit:
            await system_manager._on_shutdown_requested(event)
            mock_exit.assert_called_once_with(0)
