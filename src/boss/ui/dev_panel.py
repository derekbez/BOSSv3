"""Dev panel — hardware simulation sidebar for development on Windows/Mac.

Provides virtual buttons, switch slider, LED indicators, and 7-segment
display readout.  Routes all actions through mock hardware objects so
LED gating and the full event flow are exercised identically to real GPIO.

Only rendered when ``config.system.dev_mode is True``.
"""

from __future__ import annotations

import logging as _logging

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
    """

    def __init__(self, factory: MockHardwareFactory, event_bus: EventBus) -> None:
        self._factory = factory
        self._bus = event_bus

        # LED indicator elements (populated during build)
        self._led_badges: dict[str, ui.badge] = {}
        # 7-segment display label
        self._display_label: ui.label | None = None
        # Switch slider ref
        self._switch_slider: ui.slider | None = None
        self._switch_label: ui.label | None = None

    def build(self) -> None:
        """Render the dev panel inside the current NiceGUI page context."""
        with ui.column().classes("w-full items-center").style(
            "max-width: 840px; gap: 12px; padding-top: 4px;"
        ):
            # Collapsible panel
            with ui.expansion("Dev Panel", icon="developer_board").classes(
                "w-full"
            ).style(
                "background: #2d2d2d; border-radius: 8px; color: #ffffff;"
            ) as expansion:
                expansion.props('default-opened')
                with ui.column().classes("w-full").style(
                    "padding: 12px; gap: 16px;"
                ):
                    self._build_leds_and_buttons()
                    ui.separator().style("background: #555555;")
                    self._build_switch()
                    ui.separator().style("background: #555555;")
                    self._build_display()

        # Subscribe to output events for live updates
        self._bus.subscribe(events.LED_STATE_CHANGED, self._on_led_changed)
        self._bus.subscribe(events.DISPLAY_UPDATED, self._on_display_updated)
        self._bus.subscribe(events.SWITCH_CHANGED, self._on_switch_changed)

        # Set up keyboard shortcuts
        self._build_keyboard_handler()

    # ------------------------------------------------------------------
    # Build sections
    # ------------------------------------------------------------------

    def _build_leds_and_buttons(self) -> None:
        """LED indicators + colour buttons + Go button."""
        ui.label("Hardware Controls").style(
            "color: #00aaff; font-size: 14px; font-weight: bold;"
        )

        with ui.row().classes("w-full items-start justify-between"):
            # LEDs + buttons in a 2×2 grid
            with ui.column().classes("items-center gap-2"):
                # LED indicators row
                with ui.row().classes("gap-4"):
                    for color in ["red", "yellow", "green", "blue"]:
                        with ui.column().classes("items-center gap-1"):
                            badge = ui.badge("", color=color).style(
                                "width: 20px; height: 20px; border-radius: 50%; "
                                f"background: #444444; min-width: 20px;"
                            )
                            self._led_badges[color] = badge
                            ui.label(color.upper()).style(
                                "font-size: 10px; color: #888888;"
                            )

                # Buttons row
                with ui.row().classes("gap-2"):
                    for color in ["red", "yellow", "green", "blue"]:
                        shortcut = {"red": "1", "yellow": "2", "green": "3", "blue": "4"}
                        ui.button(
                            shortcut[color],
                            on_click=lambda _, c=color: self._on_button_click(c),
                        ).style(
                            f"background: {_BUTTON_COLORS[color]} !important; "
                            "color: white; min-width: 50px; font-weight: bold;"
                        ).tooltip(f"{color.title()} button (key: {shortcut[color]})")

            # Go button
            with ui.column().classes("items-center gap-1"):
                ui.button(
                    "GO",
                    on_click=self._on_go_click,
                ).style(
                    "background: #228B22 !important; color: white; "
                    "font-size: 18px; font-weight: bold; min-width: 80px; "
                    "min-height: 50px;"
                ).tooltip("Launch app (key: Space)")

    def _build_switch(self) -> None:
        """Switch slider (0–255) with binary display."""
        ui.label("Switch (0–255)").style(
            "color: #00aaff; font-size: 14px; font-weight: bold;"
        )

        with ui.row().classes("w-full items-center gap-4"):
            self._switch_slider = ui.slider(
                min=0, max=255, step=1, value=self._factory.switches.get_value(),
                on_change=lambda e: self._on_switch_slide(e.value),
            ).classes("flex-grow").style("color: #00aaff;")

            self._switch_label = ui.label(
                self._format_switch_value(self._factory.switches.get_value())
            ).style(
                "font-family: 'Courier New', monospace; font-size: 14px; "
                "color: #ffffff; min-width: 120px;"
            )

    def _build_display(self) -> None:
        """7-segment display readout."""
        ui.label("7-Segment Display").style(
            "color: #00aaff; font-size: 14px; font-weight: bold;"
        )
        value = self._factory.display.last_value
        text = f"{value:4d}" if value is not None else "----"
        self._display_label = ui.label(text).style(
            "font-family: 'Courier New', monospace; font-size: 32px; "
            "color: #00ff00; background: #111111; padding: 8px 16px; "
            "border-radius: 4px; text-shadow: 0 0 8px #00ff00; "
            "letter-spacing: 8px; min-width: 120px; text-align: center;"
        )

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

    def _on_switch_slide(self, value: float) -> None:
        """Simulate a switch change via mock hardware."""
        self._factory.switches.simulate_change(int(value))

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
        """Update 7-segment readout."""
        value = event.payload.get("value")
        if self._display_label:
            if value is not None:
                self._display_label.text = f"{value:4d}"
            else:
                self._display_label.text = "----"

    async def _on_switch_changed(self, event: Event) -> None:
        """Keep slider and label in sync when switch changes from elsewhere."""
        new_value = event.payload.get("new_value", 0)
        if self._switch_slider:
            self._switch_slider.value = new_value
        if self._switch_label:
            self._switch_label.text = self._format_switch_value(new_value)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _format_switch_value(value: int) -> str:
        return f"{value:3d}  ({value:08b})"
