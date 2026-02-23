"""Dev panel — hardware simulation controls for development on Windows/Mac.

Provides virtual buttons, switch slider, LED indicators, and 7-segment
display readout rendered inline below the app screen.  Routes all actions
through mock hardware objects so LED gating and the full event flow are
exercised identically to real GPIO.

Only rendered when the hardware factory is :class:`MockHardwareFactory`.
"""

from __future__ import annotations

import logging as _logging
from typing import Any

from nicegui import ui

from boss.core import events
from boss.core.event_bus import EventBus
from boss.core.models.event import Event
from boss.core.models.state import ButtonColor, LedColor
from boss.hardware.mock.mock_factory import MockHardwareFactory

_log = _logging.getLogger(__name__)

# LED colour hex values for glow effect
_LED_COLORS: dict[str, str] = {
    "red": "#ff4444",
    "yellow": "#ffff00",
    "green": "#44ff44",
    "blue": "#4444ff",
}

_BUTTON_COLORS: dict[str, str] = {
    "red": "#cc3333",
    "yellow": "#cccc00",
    "green": "#33cc33",
    "blue": "#3333cc",
}


class DevPanel:
    """Hardware simulation panel wired to mock hardware objects.

    Args:
        factory: The :class:`MockHardwareFactory` whose objects drive
            the simulation.
        event_bus: The global event bus for subscribing to output events.
        screen_width: Maximum pixel width to constrain the panel to.
    """

    def __init__(
        self,
        factory: MockHardwareFactory,
        event_bus: EventBus,
        screen_width: int = 1024,
    ) -> None:
        self._factory = factory
        self._bus = event_bus
        self._screen_width = screen_width

        # LED indicator elements (populated during build)
        self._led_badges: dict[str, ui.badge] = {}
        # 7-segment display label
        self._display_label: ui.label | None = None
        # Switch bank (8-bit) refs
        self._switch_toggles: list[Any] = []
        self._switch_label: ui.label | None = None
        self._syncing_switch_bank: bool = False

    def build(self) -> None:
        """Render the dev panel inline (no collapsible wrapper)."""
        sw = self._screen_width
        with ui.column().classes("w-full items-center").style(
            f"max-width: {sw}px; gap: 4px; padding: 2px 0 2px 0;"
        ):
            # Thin separator between screen and controls
            ui.separator().style("background: #444444; margin: 0;")

            with ui.row().classes("w-full items-start justify-between").style(
                "padding: 2px 12px; gap: 12px; flex-wrap: nowrap;"
            ):
                # Left: 7-seg + 8 toggle switches (physical switch bank)
                self._build_left_switch_bank()
                # Middle: square red GO button
                self._build_go_button()
                # Right: 4 buttons each with adjacent LED
                self._build_right_buttons_and_leds()

        # Subscribe to output events for live updates
        self._bus.subscribe(events.LED_STATE_CHANGED, self._on_led_changed)
        self._bus.subscribe(events.DISPLAY_UPDATED, self._on_display_updated)
        self._bus.subscribe(events.SWITCH_CHANGED, self._on_switch_changed)

        # Set up keyboard shortcuts
        self._build_keyboard_handler()

    # ------------------------------------------------------------------
    # Build sections
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # New physical-layout build sections
    # ------------------------------------------------------------------

    def _build_left_switch_bank(self) -> None:
        """Left side of panel: 7-seg display + 8 toggle switches (2x4)."""
        value = self._factory.display.last_value
        text = f"{value:4d}" if value is not None else "----"

        with ui.column().classes("items-start").style("gap: 8px; flex: 1 1 0;"):
            # 7-segment display readout (matches physical placement on left)
            self._display_label = ui.label(text).style(
                "font-family: 'Courier New', monospace; font-size: 28px; "
                "color: #00ff00; background: #111111; padding: 4px 12px; "
                "border-radius: 4px; text-shadow: 0 0 8px #00ff00; "
                "letter-spacing: 8px; min-width: 100px; text-align: center;"
            )

            ui.label("SWITCHES").style("color: #888888; font-size: 12px; font-weight: bold;")

            self._switch_toggles = []
            current = self._factory.switches.get_value()

            # Two rows of four toggles (8-bit bank)
            for row in (0, 1):
                with ui.row().classes("items-center").style("gap: 10px;"):
                    for col in range(4):
                        bit_index = row * 4 + col
                        is_on = bool(current & (1 << bit_index))
                        toggle = ui.switch(
                            text=str(bit_index),
                            value=is_on,
                            on_change=lambda e, b=bit_index: self._on_switch_toggle(b, bool(e.value)),
                        ).style(
                            "font-size: 11px; color: #ffffff;"
                        )
                        self._switch_toggles.append(toggle)

            self._switch_label = ui.label(self._format_switch_value(current)).style(
                "font-family: 'Courier New', monospace; font-size: 13px; "
                "color: #ffffff; min-width: 110px;"
            )

    def _build_go_button(self) -> None:
        """Middle of panel: large square red GO button."""
        with ui.column().classes("items-center justify-start").style("min-width: 90px; gap: 6px;"):
            ui.label("GO").style("color: #888888; font-size: 12px; font-weight: bold;")
            ui.button(
                "GO",
                on_click=self._on_go_click,
            ).style(
                "background: #cc3333 !important; color: white; "
                "font-size: 16px; font-weight: bold; width: 72px; height: 72px; "
                "border-radius: 6px;"
            ).tooltip("Launch app (key: Space)")

    def _build_right_buttons_and_leds(self) -> None:
        """Right side: 4 buttons with their adjacent LED indicators."""
        shortcut = {"red": "1", "yellow": "2", "green": "3", "blue": "4"}

        with ui.column().classes("items-end").style("gap: 8px; flex: 1 1 0;"):
            ui.label("BUTTONS").style("color: #888888; font-size: 12px; font-weight: bold;")

            # Arrange as a 2x2 cluster; each pair = LED + button
            colors = ["red", "yellow", "green", "blue"]
            for row in (0, 1):
                with ui.row().classes("items-center").style("gap: 14px;"):
                    for col in range(2):
                        color = colors[row * 2 + col]
                        with ui.row().classes("items-center").style("gap: 8px;"):
                            badge = ui.badge("").style(
                                "width: 18px; height: 18px; border-radius: 50%; "
                                "background: #444444; min-width: 18px;"
                            )
                            self._led_badges[color] = badge

                            ui.button(
                                shortcut[color],
                                on_click=lambda _, c=color: self._on_button_click(c),
                            ).style(
                                "background: #333333 !important; color: white; "
                                "min-width: 44px; height: 36px; font-weight: bold; padding: 0 8px;"
                            ).tooltip(f"{color.title()} button (key: {shortcut[color]})")

    def _build_keyboard_handler(self) -> None:
        """Wire keyboard shortcuts: 1-4 for buttons, Space for Go, Up/Down for switch."""
        def handle_key(e) -> None:
            if e.action.keydown:
                key = e.key
                if key == "1":
                    self._on_button_click("red")
                elif key == "2":
                    self._on_button_click("yellow")
                elif key == "3":
                    self._on_button_click("green")
                elif key == "4":
                    self._on_button_click("blue")
                elif key == " ":
                    self._on_go_click()
                elif key == "ArrowUp":
                    self._adjust_switch(1)
                elif key == "ArrowDown":
                    self._adjust_switch(-1)
                elif key.lower() == "r":
                    self._set_switch(0)
                elif key.lower() == "m":
                    self._set_switch(255)

        ui.keyboard(on_key=handle_key)

    # ------------------------------------------------------------------
    # Actions (route through mock hardware)
    # ------------------------------------------------------------------

    def _on_button_click(self, color: str) -> None:
        """Simulate a colour button press via mock hardware."""
        self._factory.buttons.simulate_press(color)

    def _on_go_click(self, _=None) -> None:
        """Simulate a Go button press via mock hardware."""
        self._factory.go_button.simulate_press()

    def _on_switch_toggle(self, bit_index: int, is_on: bool) -> None:
        """Simulate toggling a single switch bit (0..7)."""
        if self._syncing_switch_bank:
            return

        current = self._factory.switches.get_value()
        mask = 1 << bit_index
        new_val = (current | mask) if is_on else (current & ~mask)
        self._factory.switches.simulate_change(new_val)

    def _adjust_switch(self, delta: int) -> None:
        """Increment/decrement switch value."""
        new_val = self._factory.switches.get_value() + delta
        new_val = max(0, min(255, new_val))
        self._factory.switches.simulate_change(new_val)

    def _set_switch(self, value: int) -> None:
        """Set switch to a specific value."""
        self._factory.switches.simulate_change(value)

    # ------------------------------------------------------------------
    # Event handlers (update UI from event bus)
    # ------------------------------------------------------------------

    async def _on_led_changed(self, event: Event) -> None:
        """Update LED indicator when an LED state changes."""
        color = event.payload.get("color", "")
        is_on = event.payload.get("is_on", False)
        badge = self._led_badges.get(color)
        if badge:
            hex_color = _LED_COLORS.get(color, "#ffffff")
            if is_on:
                badge.style(
                    f"width: 20px; height: 20px; border-radius: 50%; "
                    f"background: {hex_color}; min-width: 20px; "
                    f"box-shadow: 0 0 12px {hex_color};"
                )
            else:
                badge.style(
                    "width: 20px; height: 20px; border-radius: 50%; "
                    "background: #444444; min-width: 20px; box-shadow: none;"
                )

    async def _on_display_updated(self, event: Event) -> None:
        """Update 7-segment readout.

        The NiceGUI elements we update may have been torn down by the time
        an event arrives (for example during application shutdown).  In that
        case writing to ``.text`` will raise ``RuntimeError``; the original
        code let the exception bubble out and triggered the event bus to
        unsubscribe the handler.  We simply ignore such errors, since the
        panel is no longer visible.
        """
        value = event.payload.get("value")
        if self._display_label:
            try:
                if value is not None:
                    self._display_label.text = f"{value:4d}"
                else:
                    self._display_label.text = "----"
            except RuntimeError:
                _log.debug("display_label client gone, ignoring update")

    async def _on_switch_changed(self, event: Event) -> None:
        """Keep the switch bank and label in sync with switch changes."""
        new_value = event.payload.get("new_value", 0)
        self._syncing_switch_bank = True
        try:
            # Update toggle states
            for bit_index, toggle in enumerate(self._switch_toggles):
                try:
                    toggle.value = bool(new_value & (1 << bit_index))
                except RuntimeError:
                    _log.debug("switch toggle client gone, ignoring update")

            # Update readout
            if self._switch_label:
                try:
                    self._switch_label.text = self._format_switch_value(new_value)
                except RuntimeError:
                    _log.debug("switch_label client gone, ignoring update")
        finally:
            self._syncing_switch_bank = False


    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _format_switch_value(value: int) -> str:
        return f"{value:3d}  ({value:08b})"
