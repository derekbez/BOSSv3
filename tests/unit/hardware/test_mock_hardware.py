"""Unit tests for mock hardware classes."""

from __future__ import annotations

from boss.core.models.state import ButtonColor, LedColor
from boss.hardware.mock.mock_hardware import (
    MockButtons,
    MockDisplay,
    MockGoButton,
    MockLeds,
    MockSpeaker,
    MockSwitches,
)


class TestMockButtons:
    """MockButtons stores callbacks and simulates presses."""

    def test_simulate_press_fires_callback(self) -> None:
        buttons = MockButtons()
        pressed: list[str] = []
        buttons.register_press_callback(
            ButtonColor.RED, lambda: pressed.append("red")
        )
        buttons.simulate_press("red")
        assert pressed == ["red"]

    def test_simulate_release_fires_callback(self) -> None:
        buttons = MockButtons()
        released: list[str] = []
        buttons.register_release_callback(
            ButtonColor.BLUE, lambda: released.append("blue")
        )
        buttons.simulate_release("blue")
        assert released == ["blue"]

    def test_no_callback_does_not_error(self) -> None:
        buttons = MockButtons()
        buttons.simulate_press("green")  # no callback — should not raise

    def test_all_four_colours(self) -> None:
        buttons = MockButtons()
        presses: list[str] = []
        for color in ButtonColor:
            buttons.register_press_callback(color, lambda c=color.value: presses.append(c))

        for color in ButtonColor:
            buttons.simulate_press(color.value)

        assert sorted(presses) == sorted([c.value for c in ButtonColor])


class TestMockGoButton:
    """MockGoButton simulates the single Go button."""

    def test_simulate_press_fires_callback(self) -> None:
        go = MockGoButton()
        fired = []
        go.register_press_callback(lambda: fired.append(True))
        go.simulate_press()
        assert fired == [True]

    def test_no_callback_does_not_error(self) -> None:
        go = MockGoButton()
        go.simulate_press()


class TestMockLeds:
    """MockLeds tracks LED state in memory."""

    def test_initial_state_all_off(self) -> None:
        leds = MockLeds()
        for color in LedColor:
            assert leds.get_state(color) is False

    def test_set_led_on(self) -> None:
        leds = MockLeds()
        leds.set_led(LedColor.RED, True)
        assert leds.get_state(LedColor.RED) is True
        assert leds.get_state(LedColor.GREEN) is False

    def test_all_off(self) -> None:
        leds = MockLeds()
        leds.set_led(LedColor.RED, True)
        leds.set_led(LedColor.BLUE, True)
        leds.all_off()
        for color in LedColor:
            assert leds.get_state(color) is False


class TestMockSwitches:
    """MockSwitches tracks switch value and fires change callbacks."""

    def test_initial_value(self) -> None:
        sw = MockSwitches(initial_value=42)
        assert sw.get_value() == 42

    def test_simulate_change_updates_value(self) -> None:
        sw = MockSwitches()
        sw.simulate_change(100)
        assert sw.get_value() == 100

    def test_simulate_change_fires_callback(self) -> None:
        sw = MockSwitches()
        changes: list[tuple[int, int]] = []
        sw.register_change_callback(lambda old, new: changes.append((old, new)))
        sw.simulate_change(50)
        assert changes == [(0, 50)]

    def test_clamps_to_0_255(self) -> None:
        sw = MockSwitches()
        sw.simulate_change(300)
        assert sw.get_value() == 255
        sw.simulate_change(-10)
        assert sw.get_value() == 0

    def test_no_callback_when_value_unchanged(self) -> None:
        sw = MockSwitches(initial_value=50)
        changes: list[tuple[int, int]] = []
        sw.register_change_callback(lambda old, new: changes.append((old, new)))
        sw.simulate_change(50)
        assert changes == []  # same value — no callback


class TestMockDisplay:
    """MockDisplay stores the current display value."""

    def test_show_number(self) -> None:
        display = MockDisplay()
        display.show_number(42)
        assert display.last_value == 42

    def test_clear(self) -> None:
        display = MockDisplay()
        display.show_number(99)
        display.clear()
        assert display.last_value is None

    def test_set_brightness(self) -> None:
        display = MockDisplay()
        display.set_brightness(3)
        assert display.brightness == 3

    def test_brightness_clamped(self) -> None:
        display = MockDisplay()
        display.set_brightness(10)
        assert display.brightness == 7
        display.set_brightness(-1)
        assert display.brightness == 0


class TestMockSpeaker:
    """MockSpeaker is log-only — just verify it doesn't crash."""

    def test_play_file(self) -> None:
        speaker = MockSpeaker()
        speaker.play_file("/tmp/beep.wav")

    def test_stop(self) -> None:
        speaker = MockSpeaker()
        speaker.stop()
