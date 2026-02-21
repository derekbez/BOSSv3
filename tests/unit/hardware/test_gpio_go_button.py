"""Tests for GPIOGoButton — mocks gpiozero so tests run on any platform."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from boss.core.interfaces.hardware import GoButtonInterface
from boss.core.models.config import HardwareConfig


def _make_config() -> HardwareConfig:
    return HardwareConfig(go_button_pin=17)


class TestGPIOGoButton:
    @patch("boss.hardware.gpio.gpio_hardware.Button")
    def test_creates_with_correct_pin(self, MockButton):
        from boss.hardware.gpio.gpio_hardware import GPIOGoButton

        GPIOGoButton(_make_config())
        MockButton.assert_called_once_with(17, pull_up=True, bounce_time=0.2)

    @patch("boss.hardware.gpio.gpio_hardware.Button")
    def test_register_press_callback(self, MockButton):
        from boss.hardware.gpio.gpio_hardware import GPIOGoButton

        mock_btn = MagicMock()
        MockButton.return_value = mock_btn
        go = GPIOGoButton(_make_config())

        cb = MagicMock()
        go.register_press_callback(cb)
        assert mock_btn.when_pressed == cb

    @patch("boss.hardware.gpio.gpio_hardware.Button")
    def test_cleanup_closes(self, MockButton):
        from boss.hardware.gpio.gpio_hardware import GPIOGoButton

        mock_btn = MagicMock()
        MockButton.return_value = mock_btn
        go = GPIOGoButton(_make_config())

        go.cleanup()
        mock_btn.close.assert_called_once()

    @patch("boss.hardware.gpio.gpio_hardware.Button")
    def test_implements_interface(self, MockButton):
        from boss.hardware.gpio.gpio_hardware import GPIOGoButton

        assert isinstance(GPIOGoButton(_make_config()), GoButtonInterface)
