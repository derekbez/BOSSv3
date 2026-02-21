"""GPIO hardware implementations for Raspberry Pi.

Each class implements the corresponding ABC from
:mod:`boss.core.interfaces.hardware` using ``gpiozero`` for buttons,
LEDs, and the 74HC151 MUX switch reader, and ``python-tm1637`` for
the 4-digit 7-segment display.

Pin factory (``LGPIOFactory``) is set **once** by
:class:`~boss.hardware.gpio.gpio_factory.GPIOHardwareFactory` before
any objects in this module are instantiated.

.. note::

   The ``gpiozero`` and ``tm1637`` imports are guarded so the module
   can be imported (but not instantiated) on non-Pi platforms for
   testing with ``unittest.mock.patch``.
"""

from __future__ import annotations

import logging as _logging
import threading
import time
from typing import Callable

from boss.core.interfaces.hardware import (
    ButtonInterface,
    DisplayInterface,
    GoButtonInterface,
    LedInterface,
    SpeakerInterface,
    SwitchInterface,
)
from boss.core.models.config import HardwareConfig
from boss.core.models.state import ButtonColor, LedColor

_log = _logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy imports — patched by unit tests on non-Pi platforms.
# The names below become module-level attributes that tests can
# ``@patch("boss.hardware.gpio.gpio_hardware.Button")`` etc.
# ---------------------------------------------------------------------------
try:
    from gpiozero import Button  # type: ignore[import-untyped]
    from gpiozero import LED  # type: ignore[import-untyped]
    from gpiozero import DigitalInputDevice, DigitalOutputDevice  # type: ignore[import-untyped]
except ImportError:  # pragma: no cover — non-Pi
    Button = None  # type: ignore[assignment,misc]
    LED = None  # type: ignore[assignment,misc]
    DigitalInputDevice = None  # type: ignore[assignment,misc]
    DigitalOutputDevice = None  # type: ignore[assignment,misc]

try:
    from tm1637 import TM1637  # type: ignore[import-untyped]
except ImportError:  # pragma: no cover
    TM1637 = None  # type: ignore[assignment,misc]


# ---------------------------------------------------------------------------
# Buttons
# ---------------------------------------------------------------------------

class GPIOButtons(ButtonInterface):
    """Four colour-coded pushbuttons via ``gpiozero.Button``.

    ``bounce_time=0.05`` provides adequate debounce for tactile switches.
    Callbacks are zero-arg as required by the V3 ABC — the
    :class:`HardwareEventBridge` captures the colour externally.
    """

    def __init__(self, config: HardwareConfig) -> None:
        self._buttons: dict[str, object] = {}
        for color in ButtonColor:
            pin = config.button_pins[color.value]
            btn = Button(pin, pull_up=True, bounce_time=0.05)
            self._buttons[color.value] = btn

        _log.info("GPIOButtons initialised: %s", {c: config.button_pins[c] for c in config.button_pins})

    # -- ABC implementation --

    def register_press_callback(
        self, color: ButtonColor, callback: Callable[[], None]
    ) -> None:
        self._buttons[color.value].when_pressed = callback  # type: ignore[attr-defined]

    def register_release_callback(
        self, color: ButtonColor, callback: Callable[[], None]
    ) -> None:
        self._buttons[color.value].when_released = callback  # type: ignore[attr-defined]

    # -- Lifecycle --

    def cleanup(self) -> None:
        for btn in self._buttons.values():
            btn.close()  # type: ignore[attr-defined]
        self._buttons.clear()
        _log.debug("GPIOButtons cleaned up")


# ---------------------------------------------------------------------------
# Go button
# ---------------------------------------------------------------------------

class GPIOGoButton(GoButtonInterface):
    """Single "Go" button with longer debounce (``0.2 s``)."""

    def __init__(self, config: HardwareConfig) -> None:
        self._button = Button(config.go_button_pin, pull_up=True, bounce_time=0.2)
        _log.info("GPIOGoButton initialised on pin %d", config.go_button_pin)

    def register_press_callback(self, callback: Callable[[], None]) -> None:
        self._button.when_pressed = callback

    def cleanup(self) -> None:
        self._button.close()
        _log.debug("GPIOGoButton cleaned up")


# ---------------------------------------------------------------------------
# LEDs
# ---------------------------------------------------------------------------

class GPIOLeds(LedInterface):
    """Four colour-coded LEDs via ``gpiozero.LED``.

    V3 interface is boolean on/off only (no PWM brightness).
    """

    def __init__(self, config: HardwareConfig) -> None:
        self._leds: dict[str, object] = {}
        self._states: dict[str, bool] = {}
        for color in LedColor:
            pin = config.led_pins[color.value]
            self._leds[color.value] = LED(pin)
            self._states[color.value] = False

        _log.info("GPIOLeds initialised: %s", {c: config.led_pins[c] for c in config.led_pins})

    # -- ABC implementation --

    def set_led(self, color: LedColor, on: bool) -> None:
        led = self._leds.get(color.value)
        if led is None:
            return
        if on:
            led.on()  # type: ignore[attr-defined]
        else:
            led.off()  # type: ignore[attr-defined]
        self._states[color.value] = on

    def get_state(self, color: LedColor) -> bool:
        return self._states.get(color.value, False)

    def all_off(self) -> None:
        for color in LedColor:
            self.set_led(color, False)

    # -- Lifecycle --

    def cleanup(self) -> None:
        self.all_off()
        for led in self._leds.values():
            led.close()  # type: ignore[attr-defined]
        self._leds.clear()
        _log.debug("GPIOLeds cleaned up")


# ---------------------------------------------------------------------------
# Switches (74HC151 multiplexer)
# ---------------------------------------------------------------------------

class GPIOSwitches(SwitchInterface):
    """8-bit switch bank read via 74HC151 multiplexer.

    A daemon thread polls the MUX at ~20 Hz (``sleep(0.05)``).
    Three select lines S0/S1/S2 cycle through the 8 switch positions,
    reading the active-low data pin for each.

    Polling starts automatically on construction.
    """

    def __init__(self, config: HardwareConfig) -> None:
        data_pin = config.switch_pins["data"]
        self._data = DigitalInputDevice(data_pin, pull_up=True)
        self._selects = [
            DigitalOutputDevice(config.mux_pins["s0"]),
            DigitalOutputDevice(config.mux_pins["s1"]),
            DigitalOutputDevice(config.mux_pins["s2"]),
        ]

        self._value: int = 0
        self._callback: Callable[[int, int], None] | None = None
        self._running = True

        self._thread = threading.Thread(
            target=self._poll_loop, name="mux-poll", daemon=True,
        )
        self._thread.start()

        _log.info(
            "GPIOSwitches initialised (data=%d, sel=%s)",
            data_pin,
            [config.mux_pins[k] for k in ("s0", "s1", "s2")],
        )

    # -- ABC implementation --

    def get_value(self) -> int:
        return self._value

    def register_change_callback(
        self, callback: Callable[[int, int], None]
    ) -> None:
        self._callback = callback

    # -- MUX read logic --

    def _read_switches(self) -> int:
        """Read all 8 switch positions and return an 8-bit integer."""
        value = 0
        for i in range(8):
            # Set select lines S0, S1, S2 for switch *i*.
            for j, sel in enumerate(self._selects):
                sel.value = (i >> j) & 1
            time.sleep(0.0005)  # 0.5 ms settle time
            # Data pin is active-low.
            if not self._data.value:
                value |= (1 << i)
        return value

    def _poll_loop(self) -> None:
        """Background polling thread (~20 Hz)."""
        while self._running:
            try:
                new_value = self._read_switches()
                if new_value != self._value:
                    old = self._value
                    self._value = new_value
                    if self._callback is not None:
                        self._callback(old, new_value)
            except Exception:
                _log.exception("Error reading MUX switches")
                time.sleep(1.0)  # back off on error
            else:
                time.sleep(0.05)  # ~20 Hz

    # -- Lifecycle --

    def cleanup(self) -> None:
        self._running = False
        self._thread.join(timeout=2.0)
        self._data.close()
        for sel in self._selects:
            sel.close()
        _log.debug("GPIOSwitches cleaned up")


# ---------------------------------------------------------------------------
# TM1637 7-segment display
# ---------------------------------------------------------------------------

class GPIODisplay(DisplayInterface):
    """TM1637 4-digit 7-segment display.

    Uses the ``python-tm1637`` package.  Brightness is integer 0–7
    (matching the V3 ABC directly).
    """

    def __init__(self, config: HardwareConfig) -> None:
        clk = config.display_clk_pin
        dio = config.display_dio_pin
        self._tm = TM1637(clk=clk, dio=dio)
        self._tm.brightness(7)  # default max
        self.clear()
        _log.info("GPIODisplay initialised (CLK=%d, DIO=%d)", clk, dio)

    # -- ABC implementation --

    def show_number(self, value: int) -> None:
        if self._tm is None:
            return
        try:
            if hasattr(self._tm, "number"):
                self._tm.number(value)
            else:
                self._tm.show(str(value).rjust(4))
        except Exception:
            _log.exception("Error showing number %d on TM1637", value)

    def clear(self) -> None:
        if self._tm is None:
            return
        try:
            if hasattr(self._tm, "show"):
                self._tm.show("    ")
            elif hasattr(self._tm, "clear"):
                self._tm.clear()
        except Exception:
            _log.exception("Error clearing TM1637")

    def set_brightness(self, level: int) -> None:
        if self._tm is None:
            return
        clamped = max(0, min(7, level))
        try:
            self._tm.brightness(clamped)
        except Exception:
            _log.exception("Error setting TM1637 brightness")

    # -- Lifecycle --

    def cleanup(self) -> None:
        if self._tm is not None:
            try:
                self.clear()
            except Exception:
                pass
            self._tm = None
        _log.debug("GPIODisplay cleaned up")


# ---------------------------------------------------------------------------
# Speaker (placeholder)
# ---------------------------------------------------------------------------

class GPIOSpeaker(SpeakerInterface):
    """Placeholder speaker — logs calls, no real audio yet."""

    def play_file(self, path: str) -> None:
        _log.info("GPIOSpeaker.play_file(%s) — not implemented", path)

    def stop(self) -> None:
        _log.debug("GPIOSpeaker.stop() — no-op")

    def cleanup(self) -> None:
        pass
