from __future__ import annotations

from unittest.mock import Mock

import pytest

from boss.core.app_launcher import AppLauncher
from boss.core.models.event import Event


class _DummyBus:
    def __init__(self) -> None:
        self.subscriptions: list[tuple[str, object]] = []

    def subscribe(self, event_type: str, handler: object) -> None:
        self.subscriptions.append((event_type, handler))

    async def publish(self, event_type: str, payload: dict) -> None:
        return None


@pytest.fixture
def launcher_parts():
    bus = _DummyBus()
    app_manager = Mock()
    app_runner = Mock()
    app_runner.is_running = False
    switches = Mock()
    leds = Mock()
    display = Mock()
    screen = Mock()
    config = Mock()

    launcher = AppLauncher(
        event_bus=bus,
        app_manager=app_manager,
        app_runner=app_runner,
        switches=switches,
        leds=leds,
        display=display,
        screen=screen,
        config=config,
        secrets=None,
    )
    return launcher, app_runner, display


@pytest.mark.asyncio
async def test_switch_change_updates_display_when_idle(launcher_parts):
    launcher, app_runner, display = launcher_parts
    app_runner.is_running = False

    event = Event(event_type="input.switch.changed", payload={"new_value": 123})
    await launcher._on_switch_changed(event)

    display.show_number.assert_called_once_with(123)


@pytest.mark.asyncio
async def test_switch_change_does_not_update_display_when_running(launcher_parts):
    launcher, app_runner, display = launcher_parts
    app_runner.is_running = True

    event = Event(event_type="input.switch.changed", payload={"new_value": 123})
    await launcher._on_switch_changed(event)

    display.show_number.assert_not_called()
