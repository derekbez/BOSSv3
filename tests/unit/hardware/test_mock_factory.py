"""Unit tests for MockHardwareFactory."""

from __future__ import annotations

from boss.core.interfaces.hardware import (
    ButtonInterface,
    DisplayInterface,
    GoButtonInterface,
    LedInterface,
    ScreenInterface,
    SpeakerInterface,
    SwitchInterface,
)
from boss.hardware.mock.mock_factory import MockHardwareFactory
from boss.hardware.mock.mock_hardware import (
    MockButtons,
    MockDisplay,
    MockGoButton,
    MockLeds,
    MockSpeaker,
    MockSwitches,
)
from boss.hardware.mock.mock_screen import InMemoryScreen


class TestMockHardwareFactory:
    """MockHardwareFactory creates all required interfaces."""

    def test_creates_all_interfaces(self) -> None:
        factory = MockHardwareFactory()
        assert isinstance(factory.create_buttons(), ButtonInterface)
        assert isinstance(factory.create_go_button(), GoButtonInterface)
        assert isinstance(factory.create_leds(), LedInterface)
        assert isinstance(factory.create_switches(), SwitchInterface)
        assert isinstance(factory.create_display(), DisplayInterface)
        assert isinstance(factory.create_screen(), ScreenInterface)
        assert isinstance(factory.create_speaker(), SpeakerInterface)

    def test_returns_mock_types(self) -> None:
        factory = MockHardwareFactory()
        assert isinstance(factory.create_buttons(), MockButtons)
        assert isinstance(factory.create_go_button(), MockGoButton)
        assert isinstance(factory.create_leds(), MockLeds)
        assert isinstance(factory.create_switches(), MockSwitches)
        assert isinstance(factory.create_display(), MockDisplay)
        assert isinstance(factory.create_speaker(), MockSpeaker)

    def test_default_screen_is_in_memory(self) -> None:
        factory = MockHardwareFactory()
        assert isinstance(factory.create_screen(), InMemoryScreen)

    def test_set_screen_replaces_default(self) -> None:
        factory = MockHardwareFactory()
        custom = InMemoryScreen()  # a second instance
        factory.set_screen(custom)
        assert factory.create_screen() is custom

    def test_returns_same_instances(self) -> None:
        """Factory stores instances as attributes — same object each call."""
        factory = MockHardwareFactory()
        assert factory.create_buttons() is factory.buttons
        assert factory.create_leds() is factory.leds
        assert factory.create_switches() is factory.switches
        assert factory.create_display() is factory.display
        assert factory.create_go_button() is factory.go_button
        assert factory.create_speaker() is factory.speaker

    def test_factory_attributes_accessible(self) -> None:
        """Dev panel and tests can access mock objects via attributes."""
        factory = MockHardwareFactory()
        assert hasattr(factory, "buttons")
        assert hasattr(factory, "go_button")
        assert hasattr(factory, "leds")
        assert hasattr(factory, "switches")
        assert hasattr(factory, "display")
        assert hasattr(factory, "speaker")
