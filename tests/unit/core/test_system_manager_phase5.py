"""Tests for SystemManager Phase 5 additions — reboot/shutdown, public properties."""

from __future__ import annotations

import asyncio
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


class TestSystemManagerProperties:
    """Test the new public properties."""

    def test_app_manager_none_before_start(self, system_manager: SystemManager) -> None:
        assert system_manager.app_manager is None

    def test_app_runner_none_before_start(self, system_manager: SystemManager) -> None:
        assert system_manager.app_runner is None

    @pytest.mark.asyncio
    async def test_app_manager_set_after_start(self, system_manager: SystemManager) -> None:
        await system_manager.start()
        assert system_manager.app_manager is not None

    @pytest.mark.asyncio
    async def test_app_runner_set_after_start(self, system_manager: SystemManager) -> None:
        await system_manager.start()
        assert system_manager.app_runner is not None


class TestShutdownActions:
    """Test the reboot/shutdown subprocess calls."""

    @pytest.mark.asyncio
    async def test_reboot_in_dev_mode_does_not_call_subprocess(self, system_manager: SystemManager) -> None:
        """In dev_mode, reboot should not call subprocess."""
        system_manager._config.system.dev_mode = True
        event = Event(event_type="system.shutdown.requested", payload={"action": "reboot", "reason": "test"})

        with patch("boss.core.system_manager.subprocess.Popen") as mock_popen, \
             patch("boss.core.system_manager.sys.exit"):
            await system_manager._on_shutdown_requested(event)
            mock_popen.assert_not_called()

    @pytest.mark.asyncio
    async def test_shutdown_in_dev_mode_does_not_call_subprocess(self, system_manager: SystemManager) -> None:
        """In dev_mode, shutdown should not call subprocess."""
        system_manager._config.system.dev_mode = True
        event = Event(event_type="system.shutdown.requested", payload={"action": "shutdown", "reason": "test"})

        with patch("boss.core.system_manager.subprocess.Popen") as mock_popen, \
             patch("boss.core.system_manager.sys.exit"):
            await system_manager._on_shutdown_requested(event)
            mock_popen.assert_not_called()

    @pytest.mark.asyncio
    async def test_reboot_on_pi_calls_subprocess(self, system_manager: SystemManager) -> None:
        """When dev_mode=False, reboot should call 'sudo reboot'."""
        system_manager._config.system.dev_mode = False
        event = Event(event_type="system.shutdown.requested", payload={"action": "reboot", "reason": "test"})

        with patch("boss.core.system_manager.subprocess.Popen") as mock_popen:
            await system_manager._on_shutdown_requested(event)
            mock_popen.assert_called_once_with(["sudo", "reboot"])

    @pytest.mark.asyncio
    async def test_shutdown_on_pi_calls_subprocess(self, system_manager: SystemManager) -> None:
        """When dev_mode=False, shutdown should call 'sudo shutdown -h now'."""
        system_manager._config.system.dev_mode = False
        event = Event(event_type="system.shutdown.requested", payload={"action": "shutdown", "reason": "test"})

        with patch("boss.core.system_manager.subprocess.Popen") as mock_popen:
            await system_manager._on_shutdown_requested(event)
            mock_popen.assert_called_once_with(["sudo", "shutdown", "-h", "now"])

    @pytest.mark.asyncio
    async def test_exit_action_calls_sys_exit(self, system_manager: SystemManager) -> None:
        """Exit action should call sys.exit(0)."""
        event = Event(event_type="system.shutdown.requested", payload={"action": "exit", "reason": "test"})

        with patch("boss.core.system_manager.sys.exit") as mock_exit:
            await system_manager._on_shutdown_requested(event)
            mock_exit.assert_called_once_with(0)
