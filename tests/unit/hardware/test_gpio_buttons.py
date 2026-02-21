"""Tests for GPIOButtons — mocks gpiozero so tests run on any platform."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from boss.core.interfaces.hardware import ButtonInterface
from boss.core.models.config import HardwareConfig
from boss.core.models.state import ButtonColor

BUTTON_PINS = {"red": 26, "yellow": 19, "green": 13, "blue": 6}


def _make_config() -> HardwareConfig:
    return HardwareConfig(button_pins=BUTTON_PINS)


@patch("boss.hardware.gpio.gpio_hardware.GPIOButtons.__init__", return_value=None)
def _raw_instance(mock_init):
    """Create a GPIOButtons without hitting real gpiozero."""
    from boss.hardware.gpio.gpio_hardware import GPIOButtons

    return GPIOButtons.__new__(GPIOButtons)


class TestGPIOButtons:
    """Unit tests for GPIOButtons with mocked gpiozero."""

    @patch("boss.hardware.gpio.gpio_hardware.Button")
    def test_creates_buttons_with_correct_pins(self, MockButton):
        from boss.hardware.gpio.gpio_hardware import GPIOButtons

        cfg = _make_config()
        buttons = GPIOButtons(cfg)

        created_pins = {call.args[0] for call in MockButton.call_args_list}
        assert created_pins == {26, 19, 13, 6}

    @patch("boss.hardware.gpio.gpio_hardware.Button")
    def test_pull_up_and_bounce_time(self, MockButton):
        from boss.hardware.gpio.gpio_hardware import GPIOButtons

        GPIOButtons(_make_config())
        for call in MockButton.call_args_list:
            assert call.kwargs.get("pull_up") is True
            assert call.kwargs.get("bounce_time") == 0.05

    @patch("boss.hardware.gpio.gpio_hardware.Button")
    def test_register_press_callback(self, MockButton):
        from boss.hardware.gpio.gpio_hardware import GPIOButtons

        mock_btn = MagicMock()
        MockButton.return_value = mock_btn
        buttons = GPIOButtons(_make_config())

        cb = MagicMock()
        buttons.register_press_callback(ButtonColor.RED, cb)
        assert mock_btn.when_pressed == cb

    @patch("boss.hardware.gpio.gpio_hardware.Button")
    def test_register_release_callback(self, MockButton):
        from boss.hardware.gpio.gpio_hardware import GPIOButtons

        mock_btn = MagicMock()
        MockButton.return_value = mock_btn
        buttons = GPIOButtons(_make_config())

        cb = MagicMock()
        buttons.register_release_callback(ButtonColor.BLUE, cb)
        assert mock_btn.when_released == cb

    @patch("boss.hardware.gpio.gpio_hardware.Button")
    def test_cleanup_closes_all(self, MockButton):
        from boss.hardware.gpio.gpio_hardware import GPIOButtons

        mock_btn = MagicMock()
        MockButton.return_value = mock_btn
        buttons = GPIOButtons(_make_config())

        buttons.cleanup()
        assert mock_btn.close.call_count == 4  # 4 colours

    @patch("boss.hardware.gpio.gpio_hardware.Button")
    def test_implements_button_interface(self, MockButton):
        from boss.hardware.gpio.gpio_hardware import GPIOButtons

        buttons = GPIOButtons(_make_config())
        assert isinstance(buttons, ButtonInterface)
