"""Mock hardware implementations for development and testing.

Each class implements the corresponding ABC from
:mod:`boss.core.interfaces.hardware` with in-memory state and
``simulate_*()`` helpers for the dev panel and tests.
"""

from __future__ import annotations

import logging
from typing import Callable

from boss.core.interfaces.hardware import (
    ButtonInterface,
    DisplayInterface,
    GoButtonInterface,
    LedInterface,
    SpeakerInterface,
    SwitchInterface,
)
from boss.core.models.state import ButtonColor, LedColor

_log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Buttons
# ---------------------------------------------------------------------------

class MockButtons(ButtonInterface):
    """In-memory colour buttons with ``simulate_*`` helpers."""

    def __init__(self) -> None:
        self._press_callbacks: dict[str, Callable[[], None]] = {}
        self._release_callbacks: dict[str, Callable[[], None]] = {}

    def register_press_callback(
        self, color: ButtonColor, callback: Callable[[], None]
    ) -> None:
        self._press_callbacks[color.value] = callback

    def register_release_callback(
        self, color: ButtonColor, callback: Callable[[], None]
    ) -> None:
        self._release_callbacks[color.value] = callback

    # -- Simulation helpers --

    def simulate_press(self, color: str) -> None:
        """Trigger the press callback for *color* (e.g. ``"red"``)."""
        cb = self._press_callbacks.get(color)
        if cb:
            cb()
        else:
            _log.debug("No press callback registered for %s", color)

    def simulate_release(self, color: str) -> None:
        """Trigger the release callback for *color*."""
        cb = self._release_callbacks.get(color)
        if cb:
            cb()
        else:
            _log.debug("No release callback registered for %s", color)


# ---------------------------------------------------------------------------
# Go Button
# ---------------------------------------------------------------------------

class MockGoButton(GoButtonInterface):
    """In-memory Go button."""

    def __init__(self) -> None:
        self._callback: Callable[[], None] | None = None

    def register_press_callback(self, callback: Callable[[], None]) -> None:
        self._callback = callback

    def simulate_press(self) -> None:
        """Trigger the Go-button press callback."""
        if self._callback:
            self._callback()
        else:
            _log.debug("No Go-button callback registered")


# ---------------------------------------------------------------------------
# LEDs
# ---------------------------------------------------------------------------

class MockLeds(LedInterface):
    """In-memory LED bank, dict-backed."""

    def __init__(self) -> None:
        self._state: dict[str, bool] = {c.value: False for c in LedColor}

    def set_led(self, color: LedColor, on: bool) -> None:
        self._state[color.value] = on

    def get_state(self, color: LedColor) -> bool:
        return self._state.get(color.value, False)

    def all_off(self) -> None:
        for color in LedColor:
            self._state[color.value] = False


# ---------------------------------------------------------------------------
# Switches
# ---------------------------------------------------------------------------

class MockSwitches(SwitchInterface):
    """In-memory 8-bit switch with ``simulate_change`` helper."""

    def __init__(self, initial_value: int = 0) -> None:
        self._value = initial_value
        self._callback: Callable[[int, int], None] | None = None

    def get_value(self) -> int:
        return self._value

    def register_change_callback(
        self, callback: Callable[[int, int], None]
    ) -> None:
        self._callback = callback

    def simulate_change(self, new_value: int) -> None:
        """Update the switch value and fire the change callback."""
        old = self._value
        self._value = max(0, min(255, new_value))
        if self._callback and old != self._value:
            self._callback(old, self._value)


# ---------------------------------------------------------------------------
# 7-segment Display
# ---------------------------------------------------------------------------

class MockDisplay(DisplayInterface):
    """In-memory TM1637 display.

    Attributes:
        last_value: The last integer shown, or ``None`` after clear.
        brightness: Current brightness (0–7).
    """

    def __init__(self) -> None:
        self.last_value: int | None = None
        self.brightness: int = 7

    def show_number(self, value: int) -> None:
        self.last_value = value

    def clear(self) -> None:
        self.last_value = None

    def set_brightness(self, level: int) -> None:
        self.brightness = max(0, min(7, level))


# ---------------------------------------------------------------------------
# Speaker
# ---------------------------------------------------------------------------

class MockSpeaker(SpeakerInterface):
    """Log-only speaker — no audio playback in mock mode."""

    def play_file(self, path: str) -> None:
        _log.info("MockSpeaker: play_file(%s)", path)

    def stop(self) -> None:
        _log.info("MockSpeaker: stop()")
