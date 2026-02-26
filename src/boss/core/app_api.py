"""AppAPI — scoped API passed to each mini-app's ``run(stop_event, api)``."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from boss.config.secrets_manager import SecretsManager
from boss.core.event_bus import EventBus
from boss.core.events import LED_STATE_CHANGED
from boss.core.interfaces.hardware import LedInterface, ScreenInterface
from boss.core.models.config import BossConfig
from boss.core.models.manifest import AppManifest
from boss.core.models.state import LedColor
from boss.log_config.logger import ContextualLogger


class _ScopedEventBus:
    """Thin wrapper that tracks all subscriptions so they can be
    bulk-unsubscribed when the app stops.
    """

    def __init__(self, bus: EventBus) -> None:
        self._bus = bus
        self._sub_ids: list[str] = []

    def subscribe(
        self,
        event_type: str,
        handler: Any,
        filter_dict: dict[str, Any] | None = None,
    ) -> str:
        sub_id = self._bus.subscribe(event_type, handler, filter_dict)
        self._sub_ids.append(sub_id)
        return sub_id

    def unsubscribe(self, sub_id: str) -> None:
        self._bus.unsubscribe(sub_id)
        try:
            self._sub_ids.remove(sub_id)
        except ValueError:
            pass

    def publish_threadsafe(
        self, event_type: str, payload: dict[str, Any] | None = None
    ) -> None:
        """Publish an event from the app's daemon thread."""
        self._bus.publish_threadsafe(event_type, payload)

    def cleanup(self) -> None:
        """Unsubscribe all remaining subscriptions for this app."""
        for sub_id in self._sub_ids:
            self._bus.unsubscribe(sub_id)
        self._sub_ids.clear()


class _HardwareAPI:
    """Convenience wrapper exposing ``set_led`` to mini-apps.

    Publishes an ``output.led.state_changed`` event after every change
    so the ``HardwareEventBridge`` can track LED state for button gating.
    """

    def __init__(self, leds: LedInterface, bus: EventBus) -> None:
        self._leds = leds
        self._bus = bus

    def set_led(self, color: str, on: bool) -> None:
        led_color = LedColor(color)
        self._leds.set_led(led_color, on)
        self._bus.publish_threadsafe(
            LED_STATE_CHANGED,
            {"color": color, "is_on": on},
        )


class AppAPI:
    """Scoped API handed to a mini-app's ``run(stop_event, api)`` call.

    Every running app gets its own ``AppAPI`` instance so resources (event
    bus subscriptions, logger context) are isolated and automatically
    cleaned up when the app finishes.
    """

    def __init__(
        self,
        app_name: str,
        app_dir: Path,
        manifest: AppManifest,
        event_bus: EventBus,
        screen: ScreenInterface,
        leds: LedInterface,
        config: BossConfig,
        secrets: SecretsManager | None = None,
        app_summaries: list[dict[str, Any]] | None = None,
        app_config_overrides: dict[str, Any] | None = None,
    ) -> None:
        self._app_name = app_name
        self._app_dir = app_dir
        self._manifest = manifest
        self._config = config
        self._secrets = secrets
        self._app_summaries = app_summaries or []
        self._app_config_overrides = app_config_overrides or {}

        # Sub-APIs
        self.screen: ScreenInterface = screen
        self.hardware = _HardwareAPI(leds, event_bus)
        self.event_bus = _ScopedEventBus(event_bus)

        # Logger
        self._logger = ContextualLogger(
            logging.getLogger(f"boss.apps.{app_name}"),
            app=app_name,
        )

    # ------------------------------------------------------------------
    # Config access
    # ------------------------------------------------------------------

    def get_app_config(self) -> dict[str, Any]:
        """Return manifest config merged with runtime overrides."""
        merged = dict(self._manifest.config)
        merged.update(self._app_config_overrides)
        return merged

    def get_webui_port(self) -> int:
        """Return the current web UI port from the system config.

        This is primarily used by mini‑apps that need to construct URLs
        pointing back to the running BOSS service.  It keeps apps from
        reaching directly into ``BossConfig`` and makes the value easy to
        mock in tests.
        """
        return self._config.system.webui_port

    def is_dev_mode(self) -> bool:
        """Return ``True`` if the system is running in developer mode.

        Apps should use this instead of inspecting ``config`` directly
        so the public API remains stable if the underlying config model
        changes.
        """
        return self._config.system.dev_mode

    def get_config_value(self, key: str, default: Any = None) -> Any:
        """Return a single config value from the manifest, with a default."""
        cfg = self.get_app_config()
        return cfg.get(key, default)

    def get_global_location(self) -> dict[str, float]:
        """Return the system-wide location as ``{"lat": …, "lon": …}``."""
        loc = self._config.system.location
        return {"lat": loc.lat, "lon": loc.lon}

    # ------------------------------------------------------------------
    # Secrets access
    # ------------------------------------------------------------------

    def get_secret(self, key: str, default: str = "") -> str:
        """Return a secret / env-var value, or *default* if not set."""
        if self._secrets is None:
            return default
        return self._secrets.get(key, default)

    # ------------------------------------------------------------------
    # App directory (for list_all_apps)
    # ------------------------------------------------------------------

    def get_all_app_summaries(self) -> list[dict[str, Any]]:
        """Return ``[{"switch": int, "name": str, "description": str}, …]``
        for every app mapped to a switch value.  Sorted by switch number.
        """
        return list(self._app_summaries)

    # ------------------------------------------------------------------
    # Path helpers
    # ------------------------------------------------------------------

    def get_app_path(self) -> Path:
        """Return the app's root directory."""
        return self._app_dir

    def get_asset_path(self, filename: str) -> Path:
        """Return the path to an asset file inside the app's ``assets/`` dir."""
        return self._app_dir / "assets" / filename

    # ------------------------------------------------------------------
    # Logging helpers
    # ------------------------------------------------------------------

    def log_debug(self, msg: str) -> None:
        self._logger.debug(msg)

    def log_info(self, msg: str) -> None:
        self._logger.info(msg)

    def log_warning(self, msg: str) -> None:
        self._logger.warning(msg)

    def log_error(self, msg: str) -> None:
        self._logger.error(msg)

    # ------------------------------------------------------------------
    # Cleanup (called by AppRunner when the app finishes)
    # ------------------------------------------------------------------

    def _cleanup(self) -> None:
        """Release all scoped resources."""
        self.event_bus.cleanup()
