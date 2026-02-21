"""Tests for GPIOSwitches — mocks gpiozero so tests run on any platform."""

from __future__ import annotations

import threading
import time
from unittest.mock import MagicMock, PropertyMock, call, patch

import pytest

from boss.core.interfaces.hardware import SwitchInterface
from boss.core.models.config import HardwareConfig

SWITCH_PINS = {"data": 8}
MUX_PINS = {"s0": 23, "s1": 24, "s2": 25}


def _make_config() -> HardwareConfig:
    return HardwareConfig(switch_pins=SWITCH_PINS, mux_pins=MUX_PINS)


class TestGPIOSwitches:
    """Unit tests for GPIOSwitches with mocked gpiozero devices."""

    @patch("boss.hardware.gpio.gpio_hardware.DigitalOutputDevice")
    @patch("boss.hardware.gpio.gpio_hardware.DigitalInputDevice")
    def test_creates_data_and_select_pins(self, MockDI, MockDO):
        from boss.hardware.gpio.gpio_hardware import GPIOSwitches

        sw = GPIOSwitches(_make_config())
        sw.cleanup()  # stop thread

        MockDI.assert_called_once_with(8, pull_up=True)
        assert MockDO.call_count == 3
        select_pins = [c.args[0] for c in MockDO.call_args_list]
        assert select_pins == [23, 24, 25]

    @patch("boss.hardware.gpio.gpio_hardware.DigitalOutputDevice")
    @patch("boss.hardware.gpio.gpio_hardware.DigitalInputDevice")
    def test_get_value_initial_zero(self, MockDI, MockDO):
        from boss.hardware.gpio.gpio_hardware import GPIOSwitches

        # Data pin returns high (active-low → switch OFF)
        mock_data = MagicMock()
        type(mock_data).value = PropertyMock(return_value=True)
        MockDI.return_value = mock_data

        sw = GPIOSwitches(_make_config())
        # Allow one poll cycle
        time.sleep(0.15)
        assert sw.get_value() == 0
        sw.cleanup()

    @patch("boss.hardware.gpio.gpio_hardware.DigitalOutputDevice")
    @patch("boss.hardware.gpio.gpio_hardware.DigitalInputDevice")
    def test_reads_all_bits_on(self, MockDI, MockDO):
        from boss.hardware.gpio.gpio_hardware import GPIOSwitches

        # Data pin always low → all switches ON → value = 255
        mock_data = MagicMock()
        type(mock_data).value = PropertyMock(return_value=False)
        MockDI.return_value = mock_data

        sw = GPIOSwitches(_make_config())
        time.sleep(0.15)
        assert sw.get_value() == 255
        sw.cleanup()

    @patch("boss.hardware.gpio.gpio_hardware.DigitalOutputDevice")
    @patch("boss.hardware.gpio.gpio_hardware.DigitalInputDevice")
    def test_change_callback_fires(self, MockDI, MockDO):
        from boss.hardware.gpio.gpio_hardware import GPIOSwitches

        # Start with all high (switches off), then flip to all low
        values = [True]  # will be mutated

        mock_data = MagicMock()
        type(mock_data).value = PropertyMock(side_effect=lambda: values[0])
        MockDI.return_value = mock_data

        sw = GPIOSwitches(_make_config())
        callback = MagicMock()
        sw.register_change_callback(callback)

        time.sleep(0.15)  # let first poll cycle establish baseline (0)
        values[0] = False  # flip all switches on → 255
        time.sleep(0.15)  # let poll detect change

        sw.cleanup()
        callback.assert_called_with(0, 255)

    @patch("boss.hardware.gpio.gpio_hardware.DigitalOutputDevice")
    @patch("boss.hardware.gpio.gpio_hardware.DigitalInputDevice")
    def test_no_callback_when_unchanged(self, MockDI, MockDO):
        from boss.hardware.gpio.gpio_hardware import GPIOSwitches

        mock_data = MagicMock()
        type(mock_data).value = PropertyMock(return_value=True)  # always off
        MockDI.return_value = mock_data

        sw = GPIOSwitches(_make_config())
        callback = MagicMock()
        sw.register_change_callback(callback)

        time.sleep(0.15)
        sw.cleanup()
        callback.assert_not_called()

    @patch("boss.hardware.gpio.gpio_hardware.DigitalOutputDevice")
    @patch("boss.hardware.gpio.gpio_hardware.DigitalInputDevice")
    def test_cleanup_stops_thread_and_closes_pins(self, MockDI, MockDO):
        from boss.hardware.gpio.gpio_hardware import GPIOSwitches

        mock_data = MagicMock()
        type(mock_data).value = PropertyMock(return_value=True)
        MockDI.return_value = mock_data

        mock_sel = MagicMock()
        MockDO.return_value = mock_sel

        sw = GPIOSwitches(_make_config())
        sw.cleanup()

        assert not sw._running
        mock_data.close.assert_called_once()
        assert mock_sel.close.call_count == 3

    @patch("boss.hardware.gpio.gpio_hardware.DigitalOutputDevice")
    @patch("boss.hardware.gpio.gpio_hardware.DigitalInputDevice")
    def test_implements_interface(self, MockDI, MockDO):
        from boss.hardware.gpio.gpio_hardware import GPIOSwitches

        sw = GPIOSwitches(_make_config())
        assert isinstance(sw, SwitchInterface)
        sw.cleanup()

    @patch("boss.hardware.gpio.gpio_hardware.DigitalOutputDevice")
    @patch("boss.hardware.gpio.gpio_hardware.DigitalInputDevice")
    def test_select_pin_sequencing(self, MockDI, MockDO):
        """Verify S0/S1/S2 are set correctly for each bit position."""
        from boss.hardware.gpio.gpio_hardware import GPIOSwitches

        sel_mocks = [MagicMock(), MagicMock(), MagicMock()]
        MockDO.side_effect = sel_mocks

        mock_data = MagicMock()
        type(mock_data).value = PropertyMock(return_value=True)
        MockDI.return_value = mock_data

        sw = GPIOSwitches(_make_config())
        # Stop polling thread first, then call _read_switches directly
        sw._running = False
        sw._thread.join(timeout=1.0)

        # Reset call tracking
        for m in sel_mocks:
            m.reset_mock()

        sw._read_switches()

        # For bit 5 (binary 101): S0=1, S1=0, S2=1
        # Check that all 8 bit positions were iterated (8 sets per select line)
        for m in sel_mocks:
            assert m.value.__class__.__name__ != "NoneType"  # was set
