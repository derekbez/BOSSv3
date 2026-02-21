"""HardwareEventBridge — wires hardware callbacks to the event bus.

Implements LED-gated button logic: a colour-button press event is only
published if the LED of that colour is currently ON.
"""

from __future__ import annotations

import logging as _logging

from boss.core.event_bus import EventBus
from boss.core import events
from boss.core.interfaces.hardware import (
    ButtonInterface,
    DisplayInterface,
    GoButtonInterface,
    LedInterface,
    SwitchInterface,
)
from boss.core.models.state import ButtonColor, LedColor

_log = _logging.getLogger(__name__)


class HardwareEventBridge:
    """Translates raw hardware callbacks into event-bus messages.

    Must be instantiated *after* the event bus has been started so that
    ``publish_threadsafe`` works.

    Args:
        event_bus: The global event bus.
        buttons: Colour-button interface.
        go_button: Go-button interface.
        leds: LED interface (read state for gating).
        switches: Switch interface.
        display: 7-segment display interface.
    """

    def __init__(
        self,
        event_bus: EventBus,
        buttons: ButtonInterface,
        go_button: GoButtonInterface,
        leds: LedInterface,
        switches: SwitchInterface,
    ) -> None:
        self._bus = event_bus
        self._leds = leds

        # Track LED states locally (updated via event subscription).
        self._led_states: dict[str, bool] = {c.value: False for c in LedColor}

        # Wire up hardware callbacks.
        for color in ButtonColor:
            buttons.register_press_callback(
                color, lambda c=color.value: self._on_button_pressed(c)
            )
            buttons.register_release_callback(
                color, lambda c=color.value: self._on_button_released(c)
            )

        go_button.register_press_callback(self._on_go_pressed)
        switches.register_change_callback(self._on_switch_changed)

        # Subscribe to LED state changes so we can gate button presses.
        self._bus.subscribe(events.LED_STATE_CHANGED, self._on_led_state_changed)

    # ------------------------------------------------------------------
    # Hardware callbacks (may be called from GPIO threads)
    # ------------------------------------------------------------------

    def _on_button_pressed(self, color: str) -> None:
        if self._led_states.get(color, False):
            self._bus.publish_threadsafe(events.BUTTON_PRESSED, {"button": color})
        else:
            _log.debug("Button %s pressed but LED is off — gated", color)

    def _on_button_released(self, color: str) -> None:
        if self._led_states.get(color, False):
            self._bus.publish_threadsafe(events.BUTTON_RELEASED, {"button": color})

    def _on_go_pressed(self) -> None:
        self._bus.publish_threadsafe(events.GO_BUTTON_PRESSED, {})

    def _on_switch_changed(self, old_value: int, new_value: int) -> None:
        self._bus.publish_threadsafe(
            events.SWITCH_CHANGED, {"old_value": old_value, "new_value": new_value}
        )

    # ------------------------------------------------------------------
    # Event handler (runs on event loop, not GPIO thread)
    # ------------------------------------------------------------------

    def _on_led_state_changed(self, event: object) -> None:
        """Update local LED state tracking from ``output.led.state_changed``."""
        from boss.core.models.event import Event

        if isinstance(event, Event):
            color = event.payload.get("color")
            is_on = event.payload.get("is_on", False)
            if color:
                self._led_states[color] = is_on
