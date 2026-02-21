"""Hardware abstraction interfaces (ABCs).

Every hardware component has a matching abstract base class here.  The GPIO
and Mock backends both implement these interfaces, ensuring parity between
production and development / test environments.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable

from boss.core.models.state import ButtonColor, LedColor


# ---------------------------------------------------------------------------
# Buttons
# ---------------------------------------------------------------------------

class ButtonInterface(ABC):
    """Four colour-coded pushbuttons (red, yellow, green, blue)."""

    @abstractmethod
    def register_press_callback(
        self, color: ButtonColor, callback: Callable[[], None]
    ) -> None:
        """Register *callback* to fire when the button of *color* is pressed."""

    @abstractmethod
    def register_release_callback(
        self, color: ButtonColor, callback: Callable[[], None]
    ) -> None:
        """Register *callback* to fire when the button of *color* is released."""


class GoButtonInterface(ABC):
    """Single "Go" button that launches the currently-selected app."""

    @abstractmethod
    def register_press_callback(self, callback: Callable[[], None]) -> None:
        """Register *callback* to fire when the Go button is pressed."""


# ---------------------------------------------------------------------------
# LEDs
# ---------------------------------------------------------------------------

class LedInterface(ABC):
    """Four colour-coded LEDs (red, yellow, green, blue)."""

    @abstractmethod
    def set_led(self, color: LedColor, on: bool) -> None:
        """Turn the LED of *color* on or off."""

    @abstractmethod
    def get_state(self, color: LedColor) -> bool:
        """Return ``True`` if the LED of *color* is currently on."""

    @abstractmethod
    def all_off(self) -> None:
        """Turn all LEDs off."""


# ---------------------------------------------------------------------------
# Switches
# ---------------------------------------------------------------------------

class SwitchInterface(ABC):
    """8-bit binary switch bank (0–255) read via 74HC151 multiplexer."""

    @abstractmethod
    def get_value(self) -> int:
        """Return the current 8-bit switch value (0–255)."""

    @abstractmethod
    def register_change_callback(
        self, callback: Callable[[int, int], None]
    ) -> None:
        """Register *callback(old_value, new_value)* for switch changes."""


# ---------------------------------------------------------------------------
# 7-segment display (TM1637)
# ---------------------------------------------------------------------------

class DisplayInterface(ABC):
    """TM1637 4-digit 7-segment display."""

    @abstractmethod
    def show_number(self, value: int) -> None:
        """Show an integer on the display."""

    @abstractmethod
    def clear(self) -> None:
        """Blank the display."""

    @abstractmethod
    def set_brightness(self, level: int) -> None:
        """Set brightness (0–7)."""


# ---------------------------------------------------------------------------
# Screen (NiceGUI-backed)
# ---------------------------------------------------------------------------

class ScreenInterface(ABC):
    """Rendering surface for mini-app output.

    All methods are safe to call from *any* thread.  The NiceGUI
    implementation marshals calls to the UI event loop internally.

    Style parameters (``**kwargs`` on ``display_text``) are handled by
    the UI layer — the interface makes no assumptions about them.
    """

    @abstractmethod
    def display_text(self, text: str, **kwargs: object) -> None:
        """Show plain text (optionally styled via *kwargs*)."""

    @abstractmethod
    def display_html(self, html: str) -> None:
        """Render arbitrary HTML."""

    @abstractmethod
    def display_image(self, image_path: str) -> None:
        """Display an image file."""

    @abstractmethod
    def display_markdown(self, markdown: str) -> None:
        """Render a Markdown string."""

    @abstractmethod
    def clear(self) -> None:
        """Clear all content from the screen."""


# ---------------------------------------------------------------------------
# Speaker
# ---------------------------------------------------------------------------

class SpeakerInterface(ABC):
    """Audio output — minimal placeholder; full impl deferred to Phase 4."""

    @abstractmethod
    def play_file(self, path: str) -> None:
        """Play an audio file (WAV/MP3)."""

    @abstractmethod
    def stop(self) -> None:
        """Stop any currently-playing audio."""


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

class HardwareFactory(ABC):
    """Creates all hardware interface implementations for the current platform."""

    @abstractmethod
    def create_buttons(self) -> ButtonInterface: ...

    @abstractmethod
    def create_go_button(self) -> GoButtonInterface: ...

    @abstractmethod
    def create_leds(self) -> LedInterface: ...

    @abstractmethod
    def create_switches(self) -> SwitchInterface: ...

    @abstractmethod
    def create_display(self) -> DisplayInterface: ...

    @abstractmethod
    def create_screen(self) -> ScreenInterface: ...

    @abstractmethod
    def create_speaker(self) -> SpeakerInterface: ...

    def cleanup(self) -> None:
        """Release hardware resources.  No-op by default (mock)."""
