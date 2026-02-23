"""Unit tests for the DevPanel UI helpers.

We don't exercise NiceGUI itself here, just the small async handlers that
respond to event-bus notifications.  The regression seen during runtime
occurred when the UI element's underlying "client" had been torn down;
setting a value/property on the element then raised ``RuntimeError`` and
`EventBus` automatically unsubscribed the handler.  Our code now swallows
those errors, so the panel can be destroyed without side effects.
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest

from boss.core import events
from boss.core.models.event import Event
from boss.hardware.mock.mock_factory import MockHardwareFactory
from boss.ui.dev_panel import DevPanel


class _BrokenValueElement:
    """Mimics a NiceGUI element whose client has already been deleted."""

    def __init__(self):
        self._value = None

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, v):
        raise RuntimeError("The client this element belongs to has been deleted.")


class _BrokenTextElement:
    @property
    def text(self):
        return ""

    @text.setter
    def text(self, t):
        raise RuntimeError("The client this element belongs to has been deleted.")


@pytest.mark.asyncio
async def test_switch_handler_ignores_runtime_error() -> None:
    panel = DevPanel(factory=MockHardwareFactory(), event_bus=MagicMock())
    panel._switch_toggles = [_BrokenValueElement() for _ in range(8)]
    panel._switch_label = _BrokenTextElement()

    ev = Event(event_type=events.SWITCH_CHANGED, payload={"new_value": 7})
    # handler should complete without raising
    await panel._on_switch_changed(ev)


@pytest.mark.asyncio
async def test_display_handler_ignores_runtime_error() -> None:
    panel = DevPanel(factory=MockHardwareFactory(), event_bus=MagicMock())
    panel._display_label = _BrokenTextElement()

    ev = Event(event_type=events.DISPLAY_UPDATED, payload={"value": 123})
    await panel._on_display_updated(ev)
