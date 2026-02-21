"""Tests for GPIODisplay — mocks python-tm1637 so tests run on any platform."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from boss.core.interfaces.hardware import DisplayInterface
from boss.core.models.config import HardwareConfig


def _make_config() -> HardwareConfig:
    return HardwareConfig(display_clk_pin=5, display_dio_pin=4)


class TestGPIODisplay:
    @patch("boss.hardware.gpio.gpio_hardware.TM1637")
    def test_creates_with_correct_pins(self, MockTM):
        from boss.hardware.gpio.gpio_hardware import GPIODisplay

        GPIODisplay(_make_config())
        MockTM.assert_called_once_with(clk=5, dio=4)

    @patch("boss.hardware.gpio.gpio_hardware.TM1637")
    def test_show_number_calls_tm_number(self, MockTM):
        from boss.hardware.gpio.gpio_hardware import GPIODisplay

        mock_tm = MagicMock()
        mock_tm.number = MagicMock()
        MockTM.return_value = mock_tm

        disp = GPIODisplay(_make_config())
        disp.show_number(42)
        mock_tm.number.assert_called_with(42)

    @patch("boss.hardware.gpio.gpio_hardware.TM1637")
    def test_show_number_fallback_to_show(self, MockTM):
        from boss.hardware.gpio.gpio_hardware import GPIODisplay

        # Create a mock that has show & brightness but NOT number
        mock_tm = MagicMock()
        del mock_tm.number  # remove auto-generated 'number' attr
        MockTM.return_value = mock_tm

        disp = GPIODisplay(_make_config())
        disp.show_number(7)
        mock_tm.show.assert_called_with("   7")  # rjust(4)

    @patch("boss.hardware.gpio.gpio_hardware.TM1637")
    def test_clear(self, MockTM):
        from boss.hardware.gpio.gpio_hardware import GPIODisplay

        mock_tm = MagicMock()
        mock_tm.show = MagicMock()
        MockTM.return_value = mock_tm

        disp = GPIODisplay(_make_config())
        mock_tm.show.reset_mock()
        disp.clear()
        mock_tm.show.assert_called_with("    ")

    @patch("boss.hardware.gpio.gpio_hardware.TM1637")
    def test_set_brightness(self, MockTM):
        from boss.hardware.gpio.gpio_hardware import GPIODisplay

        mock_tm = MagicMock()
        MockTM.return_value = mock_tm

        disp = GPIODisplay(_make_config())
        disp.set_brightness(5)
        mock_tm.brightness.assert_called_with(5)

    @patch("boss.hardware.gpio.gpio_hardware.TM1637")
    def test_set_brightness_clamped(self, MockTM):
        from boss.hardware.gpio.gpio_hardware import GPIODisplay

        mock_tm = MagicMock()
        MockTM.return_value = mock_tm

        disp = GPIODisplay(_make_config())
        disp.set_brightness(10)
        mock_tm.brightness.assert_called_with(7)
        disp.set_brightness(-1)
        mock_tm.brightness.assert_called_with(0)

    @patch("boss.hardware.gpio.gpio_hardware.TM1637")
    def test_cleanup(self, MockTM):
        from boss.hardware.gpio.gpio_hardware import GPIODisplay

        mock_tm = MagicMock()
        MockTM.return_value = mock_tm

        disp = GPIODisplay(_make_config())
        disp.cleanup()
        assert disp._tm is None

    @patch("boss.hardware.gpio.gpio_hardware.TM1637")
    def test_implements_interface(self, MockTM):
        from boss.hardware.gpio.gpio_hardware import GPIODisplay

        assert isinstance(GPIODisplay(_make_config()), DisplayInterface)
