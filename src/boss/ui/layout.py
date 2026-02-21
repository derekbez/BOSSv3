"""Main page layout — single-page NiceGUI application.

Provides the ``@ui.page('/')`` route with:
* Dark theme
* Status bar (switch value, active app, system state)
* App screen container (800×480 / 5:3 aspect)
"""

from __future__ import annotations

import logging as _logging

from nicegui import ui

from boss.core import events
from boss.core.event_bus import EventBus
from boss.core.models.config import BossConfig
from boss.core.models.event import Event
from boss.ui.screen import NiceGUIScreen

_log = _logging.getLogger(__name__)


class BossLayout:
    """Manages the main BOSS page layout and status bar state.

    Args:
        screen: The NiceGUI screen to bind into the app container.
        event_bus: The global event bus for subscribing to status updates.
        config: System configuration.
    """

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
        self._active_app: str = "—"
        self._system_state: str = "Idle"

        # UI labels (bound after page renders)
        self._lbl_switch: ui.label | None = None
        self._lbl_app: ui.label | None = None
        self._lbl_state: ui.label | None = None

    def setup_page(self) -> None:
        """Register the ``@ui.page('/')`` route."""

        @ui.page("/")
        def index():
            self._build_page()

    def _build_page(self) -> None:
        """Construct the full page layout."""
        ui.dark_mode().enable()

        # Subscribe to status-relevant events
        self._bus.subscribe(events.SWITCH_CHANGED, self._on_switch_changed)
        self._bus.subscribe(events.APP_STARTED, self._on_app_started)
        self._bus.subscribe(events.APP_FINISHED, self._on_app_finished)
        self._bus.subscribe(events.APP_ERROR, self._on_app_error)
        self._bus.subscribe(events.SYSTEM_STARTED, self._on_system_started)

        # Full-screen dark background
        ui.query("body").style("background: #1a1a1a; margin: 0; padding: 0;")

        with ui.column().classes("w-full items-center").style(
            "min-height: 100vh; padding: 8px; gap: 8px;"
        ):
            # --- Status bar ---
            self._build_status_bar()

            # --- App screen container ---
            self._build_screen_container()

    def _build_status_bar(self) -> None:
        """Render the persistent status bar at the top."""
        with ui.row().classes("w-full items-center justify-between").style(
            "max-width: 840px; background: #333333; border-radius: 8px; "
            "padding: 8px 16px; color: #ffffff; font-family: 'Segoe UI', sans-serif;"
        ):
            with ui.row().classes("items-center gap-2"):
                ui.icon("tune").style("color: #00aaff;")
                self._lbl_switch = ui.label(self._format_switch()).style(
                    "font-family: 'Courier New', monospace; font-size: 14px;"
                )

            with ui.row().classes("items-center gap-2"):
                ui.icon("apps").style("color: #00aaff;")
                self._lbl_app = ui.label(self._active_app).style(
                    "font-size: 14px;"
                )

            with ui.row().classes("items-center gap-2"):
                ui.icon("circle", color="green").props('size="xs"')
                self._lbl_state = ui.label(self._system_state).style(
                    "font-size: 14px;"
                )

    def _build_screen_container(self) -> None:
        """Render the app display area and bind the screen."""
        with ui.column().classes("items-center").style(
            "background: #000000; width: 100%; max-width: 840px; "
            "aspect-ratio: 5/3; border-radius: 8px; overflow: auto; "
            "border: 1px solid #555555;"
        ) as container:
            pass  # Content rendered dynamically by NiceGUIScreen

        self._screen.bind_container(container)

    # ------------------------------------------------------------------
    # Status bar helpers
    # ------------------------------------------------------------------

    def _format_switch(self) -> str:
        """Format switch value as ``DEC (BINARY)``."""
        return f"SW: {self._switch_value:3d}  ({self._switch_value:08b})"

    def _update_status_bar(self) -> None:
        """Push current state into the status bar labels."""
        if self._lbl_switch:
            self._lbl_switch.text = self._format_switch()
        if self._lbl_app:
            self._lbl_app.text = self._active_app
        if self._lbl_state:
            self._lbl_state.text = self._system_state

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    async def _on_switch_changed(self, event: Event) -> None:
        self._switch_value = event.payload.get("new_value", 0)
        self._update_status_bar()

    async def _on_app_started(self, event: Event) -> None:
        self._active_app = event.payload.get("app_name", "?")
        self._system_state = "Running"
        self._update_status_bar()

    async def _on_app_finished(self, event: Event) -> None:
        self._active_app = "—"
        self._system_state = "Idle"
        self._update_status_bar()

    async def _on_app_error(self, event: Event) -> None:
        self._active_app = "—"
        self._system_state = "Error"
        self._update_status_bar()

    async def _on_system_started(self, event: Event) -> None:
        self._system_state = "Idle"
        self._update_status_bar()
