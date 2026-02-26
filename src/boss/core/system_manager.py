"""SystemManager — startup & shutdown orchestration (~100 lines)."""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

from boss.config.secrets_manager import SecretsManager
from boss.core import events
from boss.core.app_launcher import AppLauncher
from boss.core.app_manager import AppManager
from boss.core.app_runner import AppRunner
from boss.core.event_bus import EventBus
from boss.core.hardware_event_bridge import HardwareEventBridge
from boss.core.interfaces.hardware import HardwareFactory
from boss.core.models.config import BossConfig
from boss.core.models.event import Event

_log = logging.getLogger(__name__)


class SystemManager:
    """Top-level orchestrator for BOSS startup and shutdown.

    All heavy logic lives in dedicated modules — this class only
    sequences init / teardown and wires components together.

    Args:
        config: Validated system configuration.
        event_bus: The global event bus (not yet started).
        hardware_factory: Platform-specific hardware factory.
        apps_dir: Path to the ``apps/`` directory.
        mappings_path: Path to ``app_mappings.json``.
        secrets: Secrets manager instance.
    """

    def __init__(
        self,
        config: BossConfig,
        event_bus: EventBus,
        hardware_factory: HardwareFactory,
        apps_dir: Path,
        mappings_path: Path,
        secrets: SecretsManager,
    ) -> None:
        self._config = config
        self._bus = event_bus
        self._factory = hardware_factory
        self._apps_dir = apps_dir
        self._mappings_path = mappings_path
        self._secrets = secrets

        # Created during start()
        self._runner: AppRunner | None = None
        self._launcher: AppLauncher | None = None
        self._bridge: HardwareEventBridge | None = None
        self._app_manager: AppManager | None = None

    # ------------------------------------------------------------------
    # Public properties
    # ------------------------------------------------------------------

    @property
    def app_manager(self) -> AppManager | None:
        """The app manager (available after ``start()``)."""
        return self._app_manager

    @property
    def app_runner(self) -> AppRunner | None:
        """The app runner (available after ``start()``)."""
        return self._runner

    # ------------------------------------------------------------------
    # Startup
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Boot the system: hardware → event bus → bridge → apps → launcher."""
        _log.info("SystemManager starting …")

        # 1. Create hardware
        buttons = self._factory.create_buttons()
        go_button = self._factory.create_go_button()
        leds = self._factory.create_leds()
        switches = self._factory.create_switches()
        display = self._factory.create_display()
        screen = self._factory.create_screen()

        # 2. Start event bus
        await self._bus.start()

        # 3. Wire hardware → event bus
        self._bridge = HardwareEventBridge(
            event_bus=self._bus,
            buttons=buttons,
            go_button=go_button,
            leds=leds,
            switches=switches,
        )

        # 4. Discover apps
        self._app_manager = AppManager(self._apps_dir, self._mappings_path, self._secrets)
        self._app_manager.scan_apps()

        # 5. Create runner & launcher
        self._runner = AppRunner(self._bus)
        self._launcher = AppLauncher(
            event_bus=self._bus,
            app_manager=self._app_manager,
            app_runner=self._runner,
            switches=switches,
            leds=leds,
            display=display,
            screen=screen,
            config=self._config,
            secrets=self._secrets,
        )

        # 6. Subscribe to shutdown requests
        self._bus.subscribe(events.SHUTDOWN_REQUESTED, self._on_shutdown_requested)

        # 7. Show initial switch value on display
        initial_sw = switches.get_value()
        display.show_number(initial_sw)
        await self._bus.publish(events.DISPLAY_UPDATED, {"value": initial_sw})

        hw_type = "gpio" if not self._config.system.dev_mode else "mock"
        await self._bus.publish(events.SYSTEM_STARTED, {"hardware_type": hw_type})
        _log.info("SystemManager started (hardware=%s)", hw_type)

    # ------------------------------------------------------------------
    # Shutdown
    # ------------------------------------------------------------------

    async def shutdown(self, reason: str = "user request") -> None:
        """Graceful shutdown: stop app → stop bus → cleanup."""
        _log.info("SystemManager shutting down: %s", reason)
        await self._bus.publish(events.SHUTDOWN_INITIATED, {"reason": reason})

        if self._runner and self._runner.is_running:
            self._runner.stop()

        await self._bus.stop()

        # Release GPIO / hardware resources (no-op on mock).
        self._factory.cleanup()

        _log.info("SystemManager shutdown complete")

    async def _on_shutdown_requested(self, event: Event) -> None:
        action = event.payload.get("action", "exit")
        reason = event.payload.get("reason", "requested")
        await self.shutdown(reason=reason)

        if action == "exit":
            _log.info("Exiting process")
            sys.exit(0)
        elif action == "reboot":
            if self._config.system.dev_mode:
                _log.warning("Reboot requested but dev_mode=True — ignoring")
            else:
                _log.info("Rebooting Pi …")
                subprocess.Popen(["sudo", "reboot"])  # noqa: S603, S607
        elif action == "shutdown":
            if self._config.system.dev_mode:
                _log.warning("Shutdown requested but dev_mode=True — ignoring")
            else:
                _log.info("Shutting down Pi …")
                subprocess.Popen(["sudo", "shutdown", "-h", "now"])  # noqa: S603, S607
