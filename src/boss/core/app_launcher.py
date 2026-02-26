"""AppLauncher — Go-button → look up app → stop current → transition → launch."""

from __future__ import annotations

import logging

from boss.config.app_runtime_config import get_app_overrides
from boss.config.secrets_manager import SecretsManager
from boss.core import events
from boss.core.app_api import AppAPI
from boss.core.app_manager import AppManager
from boss.core.app_runner import AppRunner
from boss.core.event_bus import EventBus
from boss.core.interfaces.hardware import (
    DisplayInterface,
    LedInterface,
    ScreenInterface,
    SwitchInterface,
)
from boss.core.models.config import BossConfig
from boss.core.models.event import Event
from boss.core.models.state import LedColor

_log = logging.getLogger(__name__)


class AppLauncher:
    """Orchestrates the flow from Go-button press to running a mini-app.

    Sequence:
    1. Snapshot current switch value.
    2. Look up app via :class:`AppManager`.
    3. Stop the currently-running app (if any).
    4. Brief transition feedback (flash LEDs, display app name).
    5. Create :class:`AppAPI` and launch via :class:`AppRunner`.
    6. On finish: clear screen, LEDs off, restore switch display.
    """

    def __init__(
        self,
        event_bus: EventBus,
        app_manager: AppManager,
        app_runner: AppRunner,
        switches: SwitchInterface,
        leds: LedInterface,
        display: DisplayInterface,
        screen: ScreenInterface,
        config: BossConfig,
        secrets: "SecretsManager | None" = None,
    ) -> None:
        self._bus = event_bus
        self._app_manager = app_manager
        self._runner = app_runner
        self._switches = switches
        self._leds = leds
        self._display = display
        self._screen = screen
        self._config = config
        self._secrets = secrets

        # Subscribe to Go-button and app-finished events.
        self._bus.subscribe(events.GO_BUTTON_PRESSED, self._on_go_pressed)
        self._bus.subscribe(events.APP_FINISHED, self._on_app_done)
        self._bus.subscribe(events.APP_ERROR, self._on_app_done)
        self._bus.subscribe(events.SWITCH_CHANGED, self._on_switch_changed)

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    async def _on_go_pressed(self, _event: Event) -> None:
        """Handle a Go-button press: snapshot switch → launch."""
        switch_value = self._switches.get_value()
        _log.info("Go pressed — switch value = %d", switch_value)

        await self._bus.publish(
            events.APP_LAUNCH_REQUESTED, {"switch_value": switch_value}
        )

        app_name = self._app_manager.get_app_for_switch(switch_value)
        if app_name is None:
            _log.warning("No app mapped to switch value %d", switch_value)
            self._screen.display_text(f"No app at {switch_value}")
            return

        manifest = self._app_manager.get_manifest(app_name)
        app_dir = self._app_manager.get_app_dir(app_name)
        if manifest is None or app_dir is None:
            _log.error("App %s has missing manifest or directory", app_name)
            return

        # Stop current app if running
        if self._runner.is_running:
            self._runner.stop()

        # Transition feedback
        self._transition_feedback(manifest.effective_display_name, switch_value)

        # Build app summary list for list_all_apps
        app_summaries = self._build_app_summaries()
        app_overrides = get_app_overrides(app_name)

        # Create scoped API and launch
        api = AppAPI(
            app_name=app_name,
            app_dir=app_dir,
            manifest=manifest,
            event_bus=self._bus,
            screen=self._screen,
            leds=self._leds,
            config=self._config,
            secrets=self._secrets,
            app_summaries=app_summaries,
            app_config_overrides=app_overrides,
        )

        self._runner.run_app(app_name, app_dir, manifest, api)

    async def _on_app_done(self, event: Event) -> None:
        """Post-app cleanup: clear screen, LEDs off, restore display."""
        app_name = event.payload.get("app_name", "?")
        _log.info("App %s finished — cleaning up", app_name)
        self._post_app_cleanup()

    async def _on_switch_changed(self, event: Event) -> None:
        """Reflect switch changes on display while idle."""
        if self._runner.is_running:
            return
        new_value = event.payload.get("new_value")
        if not isinstance(new_value, int):
            return
        try:
            self._display.show_number(new_value)
            await self._bus.publish(events.DISPLAY_UPDATED, {"value": new_value})
        except Exception:
            _log.debug("Could not update display for switch change")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _transition_feedback(self, app_name: str, switch_value: int) -> None:
        """Brief visual feedback during app launch."""
        self._screen.clear()
        self._screen.display_text(f"Launching {app_name}...")
        self._display.show_number(switch_value)
        self._bus.publish_threadsafe(events.DISPLAY_UPDATED, {"value": switch_value})

    def _post_app_cleanup(self) -> None:
        """Reset hardware to idle state after an app finishes."""
        self._screen.clear()
        self._leds.all_off()
        # Restore switch value on 7-segment display.
        try:
            val = self._switches.get_value()
            self._display.show_number(val)
            self._bus.publish_threadsafe(events.DISPLAY_UPDATED, {"value": val})
        except Exception:
            _log.debug("Could not restore display after app cleanup")

    def _build_app_summaries(self) -> list[dict]:
        """Return sorted list of {switch, name, description} for all mapped apps."""
        result: list[dict] = []
        all_manifests = self._app_manager.get_all_manifests()
        for sw_val, app_name in sorted(self._app_manager.get_switch_map().items()):
            m = all_manifests.get(app_name)
            if m:
                result.append(
                    {"switch": sw_val, "name": m.effective_display_name, "description": m.description}
                )
        return result
        return result
