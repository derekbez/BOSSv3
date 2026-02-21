"""Tests for GPIOLeds — mocks gpiozero so tests run on any platform."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from boss.core.interfaces.hardware import LedInterface
from boss.core.models.config import HardwareConfig
from boss.core.models.state import LedColor

LED_PINS = {"red": 21, "yellow": 20, "green": 16, "blue": 12}


def _make_config() -> HardwareConfig:
    return HardwareConfig(led_pins=LED_PINS)


class TestGPIOLeds:
    @patch("boss.hardware.gpio.gpio_hardware.LED")
    def test_creates_leds_with_correct_pins(self, MockLED):
        from boss.hardware.gpio.gpio_hardware import GPIOLeds

        GPIOLeds(_make_config())
        created_pins = {call.args[0] for call in MockLED.call_args_list}
        assert created_pins == {21, 20, 16, 12}

    @patch("boss.hardware.gpio.gpio_hardware.LED")
    def test_set_led_on(self, MockLED):
        from boss.hardware.gpio.gpio_hardware import GPIOLeds

        mock_led = MagicMock()
        MockLED.return_value = mock_led
        leds = GPIOLeds(_make_config())

        leds.set_led(LedColor.RED, True)
        mock_led.on.assert_called()
        assert leds.get_state(LedColor.RED) is True

    @patch("boss.hardware.gpio.gpio_hardware.LED")
    def test_set_led_off(self, MockLED):
        from boss.hardware.gpio.gpio_hardware import GPIOLeds

        mock_led = MagicMock()
        MockLED.return_value = mock_led
        leds = GPIOLeds(_make_config())

        leds.set_led(LedColor.GREEN, True)
        leds.set_led(LedColor.GREEN, False)
        mock_led.off.assert_called()
        assert leds.get_state(LedColor.GREEN) is False

    @patch("boss.hardware.gpio.gpio_hardware.LED")
    def test_get_state_default_false(self, MockLED):
        from boss.hardware.gpio.gpio_hardware import GPIOLeds

        leds = GPIOLeds(_make_config())
        for color in LedColor:
            assert leds.get_state(color) is False

    @patch("boss.hardware.gpio.gpio_hardware.LED")
    def test_all_off(self, MockLED):
        from boss.hardware.gpio.gpio_hardware import GPIOLeds

        mock_led = MagicMock()
        MockLED.return_value = mock_led
        leds = GPIOLeds(_make_config())

        for color in LedColor:
            leds.set_led(color, True)
        leds.all_off()
        for color in LedColor:
            assert leds.get_state(color) is False

    @patch("boss.hardware.gpio.gpio_hardware.LED")
    def test_cleanup_closes_all(self, MockLED):
        from boss.hardware.gpio.gpio_hardware import GPIOLeds

        mock_led = MagicMock()
        MockLED.return_value = mock_led
        leds = GPIOLeds(_make_config())

        leds.cleanup()
        assert mock_led.close.call_count == 4

    @patch("boss.hardware.gpio.gpio_hardware.LED")
    def test_implements_interface(self, MockLED):
        from boss.hardware.gpio.gpio_hardware import GPIOLeds

        assert isinstance(GPIOLeds(_make_config()), LedInterface)
