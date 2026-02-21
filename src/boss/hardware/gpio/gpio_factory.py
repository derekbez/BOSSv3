"""GPIOHardwareFactory — creates real GPIO hardware on Raspberry Pi.

Sets the ``gpiozero`` pin factory to ``LGPIOFactory`` once during
construction, then eagerly creates all hardware component instances.

The NiceGUI screen is injected from :func:`boss.main.main` via
:meth:`set_screen` — the GPIO layer never creates its own screen.
"""

from __future__ import annotations

import logging as _logging

from boss.core.interfaces.hardware import (
    ButtonInterface,
    DisplayInterface,
    GoButtonInterface,
    HardwareFactory,
    LedInterface,
    ScreenInterface,
    SpeakerInterface,
    SwitchInterface,
)
from boss.core.models.config import BossConfig
from boss.hardware.gpio.gpio_hardware import (
    GPIOButtons,
    GPIODisplay,
    GPIOGoButton,
    GPIOLeds,
    GPIOSpeaker,
    GPIOSwitches,
)

_log = _logging.getLogger(__name__)


def _setup_pin_factory() -> None:
    """Configure gpiozero to use ``LGPIOFactory`` (for Pi 5 compat)."""
    try:
        from gpiozero import Device  # type: ignore[import-untyped]
        from gpiozero.pins.lgpio import LGPIOFactory  # type: ignore[import-untyped]

        Device.pin_factory = LGPIOFactory()
        _log.info("gpiozero pin factory set to LGPIOFactory")
    except ImportError:
        _log.warning(
            "LGPIOFactory not available — using gpiozero default pin factory"
        )


class GPIOHardwareFactory(HardwareFactory):
    """Factory that creates real GPIO-backed hardware components.

    All components are created eagerly in ``__init__`` so that
    :meth:`cleanup` can reliably close every resource.

    Args:
        config: Full system configuration (pin numbers in ``config.hardware``).
    """

    def __init__(self, config: BossConfig) -> None:
        _setup_pin_factory()

        hw = config.hardware
        self._buttons = GPIOButtons(hw)
        self._go_button = GPIOGoButton(hw)
        self._leds = GPIOLeds(hw)
        self._switches = GPIOSwitches(hw)
        self._display = GPIODisplay(hw)
        self._speaker = GPIOSpeaker()
        self._screen: ScreenInterface | None = None

        _log.info("GPIOHardwareFactory ready")

    # -- Screen injection (called from main.py) --

    def set_screen(self, screen: ScreenInterface) -> None:
        """Inject the :class:`NiceGUIScreen` before the system starts."""
        self._screen = screen

    # -- Factory interface --

    def create_buttons(self) -> ButtonInterface:
        return self._buttons

    def create_go_button(self) -> GoButtonInterface:
        return self._go_button

    def create_leds(self) -> LedInterface:
        return self._leds

    def create_switches(self) -> SwitchInterface:
        return self._switches

    def create_display(self) -> DisplayInterface:
        return self._display

    def create_screen(self) -> ScreenInterface:
        if self._screen is None:
            raise RuntimeError(
                "NiceGUIScreen not injected — call set_screen() before start()"
            )
        return self._screen

    def create_speaker(self) -> SpeakerInterface:
        return self._speaker

    # -- Lifecycle --

    def cleanup(self) -> None:
        """Release all GPIO resources and stop the MUX polling thread."""
        for name, component in [
            ("buttons", self._buttons),
            ("go_button", self._go_button),
            ("leds", self._leds),
            ("switches", self._switches),
            ("display", self._display),
            ("speaker", self._speaker),
        ]:
            try:
                component.cleanup()
            except Exception:
                _log.exception("Error cleaning up %s", name)
        _log.info("GPIOHardwareFactory cleanup complete")
