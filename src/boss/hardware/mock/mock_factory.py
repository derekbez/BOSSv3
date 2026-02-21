"""MockHardwareFactory — creates in-memory hardware for dev and test.

All created instances are stored as public attributes so the dev panel
and tests can access ``simulate_*()`` helpers directly.
"""

from __future__ import annotations

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
from boss.hardware.mock.mock_hardware import (
    MockButtons,
    MockDisplay,
    MockGoButton,
    MockLeds,
    MockSpeaker,
    MockSwitches,
)
from boss.hardware.mock.mock_screen import InMemoryScreen


class MockHardwareFactory(HardwareFactory):
    """Factory that returns in-memory mock implementations.

    After creation, the individual mock objects are available as attributes
    (e.g. ``factory.buttons``, ``factory.leds``) for direct access in
    the dev panel and tests.

    By default ``create_screen()`` returns an :class:`InMemoryScreen`.
    Call :meth:`set_screen` to inject a different screen implementation
    (e.g. :class:`NiceGUIScreen`) before the system is started.
    """

    def __init__(self) -> None:
        self.buttons = MockButtons()
        self.go_button = MockGoButton()
        self.leds = MockLeds()
        self.switches = MockSwitches()
        self.display = MockDisplay()
        self.speaker = MockSpeaker()
        self._screen: ScreenInterface = InMemoryScreen()

    def set_screen(self, screen: ScreenInterface) -> None:
        """Replace the default :class:`InMemoryScreen` with *screen*.

        Must be called **before** :meth:`create_screen` is used by
        :class:`SystemManager`.
        """
        self._screen = screen

    # -- Factory interface --

    def create_buttons(self) -> ButtonInterface:
        return self.buttons

    def create_go_button(self) -> GoButtonInterface:
        return self.go_button

    def create_leds(self) -> LedInterface:
        return self.leds

    def create_switches(self) -> SwitchInterface:
        return self.switches

    def create_display(self) -> DisplayInterface:
        return self.display

    def create_screen(self) -> ScreenInterface:
        return self._screen

    def create_speaker(self) -> SpeakerInterface:
        return self.speaker
