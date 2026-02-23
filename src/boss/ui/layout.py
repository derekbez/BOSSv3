"""Main page layout — single-page NiceGUI application.

Provides the ``@ui.page('/')`` route with:
* Dark theme
* Compact status bar (switch number + mapped app name)
* Full-bleed app screen container (minimal margins for kiosk)
"""

from __future__ import annotations

import logging as _logging
from typing import Callable

from nicegui import ui

from boss.core import events
from boss.core.event_bus import EventBus
from boss.core.models.config import BossConfig
from boss.core.models.event import Event
from boss.ui.screen import NiceGUIScreen

_log = _logging.getLogger(__name__)

# Type alias: resolver(switch_value) → (app_dir_name | None, display_name | None)
AppResolver = Callable[[int], tuple[str | None, str | None]]


def _null_resolver(_value: int) -> tuple[str | None, str | None]:
    return None, None


class BossLayout:
    """Manages the main BOSS page layout and status bar state.

    Args:
        screen: The NiceGUI screen to bind into the app container.
        event_bus: The global event bus for subscribing to status updates.
        config: System configuration.
    """

    # Height of the status bar in px (used to compute screen container size)
    _STATUS_BAR_HEIGHT = 32

    def __init__(
        self,
        screen: NiceGUIScreen,
        event_bus: EventBus,
        config: BossConfig,
    ) -> None:
        self._screen = screen
        self._bus = event_bus
        self._config = config

        # Status bar state
        self._switch_value: int = 0
        self._app_display_name: str = "—"

        # App name resolver (set after startup via set_app_resolver)
        self._resolve_app: AppResolver = _null_resolver

        # UI labels (bound after page renders)
        self._lbl_switch: ui.label | None = None
        self._lbl_app: ui.label | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_app_resolver(self, resolver: AppResolver) -> None:
        """Inject a callable that maps switch value → (dir_name, display_name).

        Called after :class:`SystemManager` starts so that the layout can
        resolve switch values to human-readable app names.
        """
        self._resolve_app = resolver

    def setup_page(self) -> None:
        """Register the ``@ui.page('/')`` route."""

        @ui.page("/")
        def index():
            self._build_page()

    def _build_page(self) -> None:
        """Construct the full page layout."""
        ui.dark_mode().enable()

        screen_width = self._config.hardware.screen_width
        screen_height = self._config.hardware.screen_height
        screen_ratio = screen_width / screen_height

        # Subscribe to status-relevant events
        self._bus.subscribe(events.SWITCH_CHANGED, self._on_switch_changed)
        self._bus.subscribe(events.APP_STARTED, self._on_app_started)
        self._bus.subscribe(events.APP_FINISHED, self._on_app_finished)
        self._bus.subscribe(events.APP_ERROR, self._on_app_error)

        # Full-screen dark background.  When running in dev mode we allow
        # the page to scroll so the on‑screen dev panel remains reachable;
        # on kiosks (dev_mode=False) we hide the scrollbar to keep the UI
        # clean.
        overflow_value = "auto" if self._config.system.dev_mode else "hidden"
        ui.query("body").style(
            f"background: #1a1a1a; margin: 0; padding: 0; overflow: {overflow_value};"
        )

        with ui.column().classes("w-full items-center").style(
            "min-height: 100vh; padding: 0 4px; gap: 0;"
        ):
            # --- Compact status bar ---
            self._build_status_bar(screen_width)

            # --- App screen container (full-bleed) ---
            self._build_screen_container(screen_width, screen_height, screen_ratio)

    def _build_status_bar(self, screen_width: int) -> None:
        """Render a slim status bar: switch number + mapped app name."""
        with ui.row().classes("w-full items-center justify-between").style(
            f"max-width: {screen_width}px; background: #333333; "
            f"height: {self._STATUS_BAR_HEIGHT}px; "
            "padding: 0 12px; color: #ffffff; font-family: 'Segoe UI', sans-serif;"
        ):
            self._lbl_switch = ui.label(self._format_switch()).style(
                "font-family: 'Courier New', monospace; font-size: 14px;"
            )
            self._lbl_app = ui.label(self._app_display_name).style(
                "font-size: 14px; color: #aaaaaa;"
            )

    def _build_screen_container(
        self,
        screen_width: int,
        screen_height: int,
        screen_ratio: float,
    ) -> None:
        """Render the app display area and bind the screen."""
        bar_h = self._STATUS_BAR_HEIGHT

        # In kiosk mode we maximize the screen to the available viewport height.
        # In dev mode we keep the screen at its configured pixel size so the
        # on-screen dev panel can sit directly underneath without a large gap.
        if self._config.system.dev_mode:
            width_rule = f"min(100%, {screen_width}px)"
        else:
            width_rule = f"min(100%, calc((100vh - {bar_h}px) * {screen_ratio:.6f}))"

        with ui.column().classes("items-center").style(
            "background: #000000; "
            f"width: {width_rule}; "
            f"max-width: {screen_width}px; "
            f"aspect-ratio: {screen_width}/{screen_height}; "
            "margin: 0; "
            "overflow: hidden;"
        ) as container:
            pass  # Content rendered dynamically by NiceGUIScreen

        self._screen.bind_container(container)

    # ------------------------------------------------------------------
    # Status bar helpers
    # ------------------------------------------------------------------

    def _format_switch(self) -> str:
        """Format switch value as ``DEC (BINARY)``."""
        return f"SW: {self._switch_value:3d}  ({self._switch_value:08b})"

    def _resolve_and_format_app_name(self) -> str:
        """Use the resolver to get the display name for the current switch value."""
        _, display_name = self._resolve_app(self._switch_value)
        return display_name or "—"

    def _update_status_bar(self) -> None:
        """Push current state into the status bar labels."""
        if self._lbl_switch:
            self._lbl_switch.text = self._format_switch()
        if self._lbl_app:
            self._lbl_app.text = self._app_display_name

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    async def _on_switch_changed(self, event: Event) -> None:
        self._switch_value = event.payload.get("new_value", 0)
        self._app_display_name = self._resolve_and_format_app_name()
        self._update_status_bar()

    async def _on_app_started(self, event: Event) -> None:
        self._app_display_name = event.payload.get(
            "display_name", event.payload.get("app_name", "?")
        )
        self._update_status_bar()

    async def _on_app_finished(self, event: Event) -> None:
        self._app_display_name = self._resolve_and_format_app_name()
        self._update_status_bar()

    async def _on_app_error(self, event: Event) -> None:
        self._app_display_name = self._resolve_and_format_app_name()
        self._update_status_bar()
