"""Tests for GPIOHardwareFactory — mocks all GPIO classes."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

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
from boss.core.models.config import BossConfig, HardwareConfig


def _make_config() -> BossConfig:
    return BossConfig(
        hardware=HardwareConfig(
            switch_pins={"data": 8},
            mux_pins={"s0": 23, "s1": 24, "s2": 25},
            button_pins={"red": 26, "yellow": 19, "green": 13, "blue": 6},
            go_button_pin=17,
            led_pins={"red": 21, "yellow": 20, "green": 16, "blue": 12},
            display_clk_pin=5,
            display_dio_pin=4,
        ),
    )


# Patch all hardware classes to avoid real GPIO
_GPIO_PATCHES = {
    "boss.hardware.gpio.gpio_hardware.Button": MagicMock,
    "boss.hardware.gpio.gpio_hardware.LED": MagicMock,
    "boss.hardware.gpio.gpio_hardware.DigitalInputDevice": MagicMock,
    "boss.hardware.gpio.gpio_hardware.DigitalOutputDevice": MagicMock,
    "boss.hardware.gpio.gpio_hardware.TM1637": MagicMock,
    "boss.hardware.gpio.gpio_factory._setup_pin_factory": lambda: None,
}


def _patch_all():
    """Return a context-manager stack that patches all GPIO imports."""
    import contextlib

    return contextlib.ExitStack()


class TestGPIOHardwareFactory:
    @patch("boss.hardware.gpio.gpio_factory._setup_pin_factory")
    @patch("boss.hardware.gpio.gpio_hardware.TM1637", new_callable=MagicMock)
    @patch("boss.hardware.gpio.gpio_hardware.DigitalOutputDevice", new_callable=MagicMock)
    @patch("boss.hardware.gpio.gpio_hardware.DigitalInputDevice", new_callable=MagicMock)
    @patch("boss.hardware.gpio.gpio_hardware.LED", new_callable=MagicMock)
    @patch("boss.hardware.gpio.gpio_hardware.Button", new_callable=MagicMock)
    def _make_factory(self, MockButton, MockLED, MockDI, MockDO, MockTM, MockSetup):
        from boss.hardware.gpio.gpio_factory import GPIOHardwareFactory

        factory = GPIOHardwareFactory(_make_config())
        return factory

    @patch("boss.hardware.gpio.gpio_factory._setup_pin_factory")
    @patch("boss.hardware.gpio.gpio_hardware.TM1637", new_callable=MagicMock)
    @patch("boss.hardware.gpio.gpio_hardware.DigitalOutputDevice", new_callable=MagicMock)
    @patch("boss.hardware.gpio.gpio_hardware.DigitalInputDevice", new_callable=MagicMock)
    @patch("boss.hardware.gpio.gpio_hardware.LED", new_callable=MagicMock)
    @patch("boss.hardware.gpio.gpio_hardware.Button", new_callable=MagicMock)
    def test_implements_hardware_factory(self, *mocks):
        from boss.hardware.gpio.gpio_factory import GPIOHardwareFactory

        factory = GPIOHardwareFactory(_make_config())
        assert isinstance(factory, HardwareFactory)
        factory.cleanup()

    @patch("boss.hardware.gpio.gpio_factory._setup_pin_factory")
    @patch("boss.hardware.gpio.gpio_hardware.TM1637", new_callable=MagicMock)
    @patch("boss.hardware.gpio.gpio_hardware.DigitalOutputDevice", new_callable=MagicMock)
    @patch("boss.hardware.gpio.gpio_hardware.DigitalInputDevice", new_callable=MagicMock)
    @patch("boss.hardware.gpio.gpio_hardware.LED", new_callable=MagicMock)
    @patch("boss.hardware.gpio.gpio_hardware.Button", new_callable=MagicMock)
    def test_create_buttons_returns_button_interface(self, *mocks):
        from boss.hardware.gpio.gpio_factory import GPIOHardwareFactory

        factory = GPIOHardwareFactory(_make_config())
        assert isinstance(factory.create_buttons(), ButtonInterface)
        factory.cleanup()

    @patch("boss.hardware.gpio.gpio_factory._setup_pin_factory")
    @patch("boss.hardware.gpio.gpio_hardware.TM1637", new_callable=MagicMock)
    @patch("boss.hardware.gpio.gpio_hardware.DigitalOutputDevice", new_callable=MagicMock)
    @patch("boss.hardware.gpio.gpio_hardware.DigitalInputDevice", new_callable=MagicMock)
    @patch("boss.hardware.gpio.gpio_hardware.LED", new_callable=MagicMock)
    @patch("boss.hardware.gpio.gpio_hardware.Button", new_callable=MagicMock)
    def test_create_go_button_returns_interface(self, *mocks):
        from boss.hardware.gpio.gpio_factory import GPIOHardwareFactory

        factory = GPIOHardwareFactory(_make_config())
        assert isinstance(factory.create_go_button(), GoButtonInterface)
        factory.cleanup()

    @patch("boss.hardware.gpio.gpio_factory._setup_pin_factory")
    @patch("boss.hardware.gpio.gpio_hardware.TM1637", new_callable=MagicMock)
    @patch("boss.hardware.gpio.gpio_hardware.DigitalOutputDevice", new_callable=MagicMock)
    @patch("boss.hardware.gpio.gpio_hardware.DigitalInputDevice", new_callable=MagicMock)
    @patch("boss.hardware.gpio.gpio_hardware.LED", new_callable=MagicMock)
    @patch("boss.hardware.gpio.gpio_hardware.Button", new_callable=MagicMock)
    def test_create_leds_returns_interface(self, *mocks):
        from boss.hardware.gpio.gpio_factory import GPIOHardwareFactory

        factory = GPIOHardwareFactory(_make_config())
        assert isinstance(factory.create_leds(), LedInterface)
        factory.cleanup()

    @patch("boss.hardware.gpio.gpio_factory._setup_pin_factory")
    @patch("boss.hardware.gpio.gpio_hardware.TM1637", new_callable=MagicMock)
    @patch("boss.hardware.gpio.gpio_hardware.DigitalOutputDevice", new_callable=MagicMock)
    @patch("boss.hardware.gpio.gpio_hardware.DigitalInputDevice", new_callable=MagicMock)
    @patch("boss.hardware.gpio.gpio_hardware.LED", new_callable=MagicMock)
    @patch("boss.hardware.gpio.gpio_hardware.Button", new_callable=MagicMock)
    def test_create_switches_returns_interface(self, *mocks):
        from boss.hardware.gpio.gpio_factory import GPIOHardwareFactory

        factory = GPIOHardwareFactory(_make_config())
        assert isinstance(factory.create_switches(), SwitchInterface)
        factory.cleanup()

    @patch("boss.hardware.gpio.gpio_factory._setup_pin_factory")
    @patch("boss.hardware.gpio.gpio_hardware.TM1637", new_callable=MagicMock)
    @patch("boss.hardware.gpio.gpio_hardware.DigitalOutputDevice", new_callable=MagicMock)
    @patch("boss.hardware.gpio.gpio_hardware.DigitalInputDevice", new_callable=MagicMock)
    @patch("boss.hardware.gpio.gpio_hardware.LED", new_callable=MagicMock)
    @patch("boss.hardware.gpio.gpio_hardware.Button", new_callable=MagicMock)
    def test_create_display_returns_interface(self, *mocks):
        from boss.hardware.gpio.gpio_factory import GPIOHardwareFactory

        factory = GPIOHardwareFactory(_make_config())
        assert isinstance(factory.create_display(), DisplayInterface)
        factory.cleanup()

    @patch("boss.hardware.gpio.gpio_factory._setup_pin_factory")
    @patch("boss.hardware.gpio.gpio_hardware.TM1637", new_callable=MagicMock)
    @patch("boss.hardware.gpio.gpio_hardware.DigitalOutputDevice", new_callable=MagicMock)
    @patch("boss.hardware.gpio.gpio_hardware.DigitalInputDevice", new_callable=MagicMock)
    @patch("boss.hardware.gpio.gpio_hardware.LED", new_callable=MagicMock)
    @patch("boss.hardware.gpio.gpio_hardware.Button", new_callable=MagicMock)
    def test_set_screen_and_create_screen(self, *mocks):
        from boss.hardware.gpio.gpio_factory import GPIOHardwareFactory

        factory = GPIOHardwareFactory(_make_config())
        mock_screen = MagicMock(spec=ScreenInterface)
        factory.set_screen(mock_screen)
        assert factory.create_screen() is mock_screen
        factory.cleanup()

    @patch("boss.hardware.gpio.gpio_factory._setup_pin_factory")
    @patch("boss.hardware.gpio.gpio_hardware.TM1637", new_callable=MagicMock)
    @patch("boss.hardware.gpio.gpio_hardware.DigitalOutputDevice", new_callable=MagicMock)
    @patch("boss.hardware.gpio.gpio_hardware.DigitalInputDevice", new_callable=MagicMock)
    @patch("boss.hardware.gpio.gpio_hardware.LED", new_callable=MagicMock)
    @patch("boss.hardware.gpio.gpio_hardware.Button", new_callable=MagicMock)
    def test_create_screen_raises_without_set(self, *mocks):
        from boss.hardware.gpio.gpio_factory import GPIOHardwareFactory

        factory = GPIOHardwareFactory(_make_config())
        with pytest.raises(RuntimeError, match="NiceGUIScreen not injected"):
            factory.create_screen()
        factory.cleanup()

    @patch("boss.hardware.gpio.gpio_factory._setup_pin_factory")
    @patch("boss.hardware.gpio.gpio_hardware.TM1637", new_callable=MagicMock)
    @patch("boss.hardware.gpio.gpio_hardware.DigitalOutputDevice", new_callable=MagicMock)
    @patch("boss.hardware.gpio.gpio_hardware.DigitalInputDevice", new_callable=MagicMock)
    @patch("boss.hardware.gpio.gpio_hardware.LED", new_callable=MagicMock)
    @patch("boss.hardware.gpio.gpio_hardware.Button", new_callable=MagicMock)
    def test_create_speaker_returns_interface(self, *mocks):
        from boss.hardware.gpio.gpio_factory import GPIOHardwareFactory

        factory = GPIOHardwareFactory(_make_config())
        assert isinstance(factory.create_speaker(), SpeakerInterface)
        factory.cleanup()

    @patch("boss.hardware.gpio.gpio_factory._setup_pin_factory")
    @patch("boss.hardware.gpio.gpio_hardware.TM1637", new_callable=MagicMock)
    @patch("boss.hardware.gpio.gpio_hardware.DigitalOutputDevice", new_callable=MagicMock)
    @patch("boss.hardware.gpio.gpio_hardware.DigitalInputDevice", new_callable=MagicMock)
    @patch("boss.hardware.gpio.gpio_hardware.LED", new_callable=MagicMock)
    @patch("boss.hardware.gpio.gpio_hardware.Button", new_callable=MagicMock)
    def test_cleanup_does_not_raise(self, *mocks):
        """Cleanup should be idempotent and not raise."""
        from boss.hardware.gpio.gpio_factory import GPIOHardwareFactory

        factory = GPIOHardwareFactory(_make_config())
        factory.cleanup()
        factory.cleanup()  # second call should be safe
