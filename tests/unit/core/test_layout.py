"""Tests for BossLayout — status bar, app resolver, event handling."""

from __future__ import annotations

import pytest

from boss.core.models.event import Event
from boss.ui.layout import BossLayout, _null_resolver


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _StubBus:
    def __init__(self) -> None:
        self._handlers: dict[str, list] = {}

    def subscribe(self, event_type: str, handler: object) -> str:
        self._handlers.setdefault(event_type, []).append(handler)
        return f"sub-{event_type}"

    async def publish(self, event_type: str, payload: dict) -> None:
        pass


class _StubScreen:
    def bind_container(self, container):
        pass


class _StubConfig:
    class hardware:
        screen_width = 1024
        screen_height = 600


# ---------------------------------------------------------------------------
# Unit tests (no NiceGUI — test logic only)
# ---------------------------------------------------------------------------


def test_null_resolver_returns_none():
    assert _null_resolver(42) == (None, None)


def test_format_switch():
    layout = BossLayout.__new__(BossLayout)
    layout._switch_value = 42
    assert layout._format_switch() == "SW:  42  (00101010)"


def test_format_switch_zero():
    layout = BossLayout.__new__(BossLayout)
    layout._switch_value = 0
    assert layout._format_switch() == "SW:   0  (00000000)"


def test_resolve_and_format_app_name_with_resolver():
    layout = BossLayout.__new__(BossLayout)
    layout._switch_value = 5
    layout._resolve_app = lambda v: ("hello", "Hello World")
    assert layout._resolve_and_format_app_name() == "Hello World"


def test_resolve_and_format_app_name_no_match():
    layout = BossLayout.__new__(BossLayout)
    layout._switch_value = 99
    layout._resolve_app = lambda v: (None, None)
    assert layout._resolve_and_format_app_name() == "—"


def test_set_app_resolver():
    layout = BossLayout.__new__(BossLayout)
    layout._resolve_app = _null_resolver
    resolver = lambda v: ("x", "X App")
    layout.set_app_resolver(resolver)
    assert layout._resolve_app is resolver


@pytest.mark.asyncio
async def test_on_switch_changed_updates_app_name():
    layout = BossLayout.__new__(BossLayout)
    layout._switch_value = 0
    layout._app_display_name = "—"
    layout._lbl_switch = None
    layout._lbl_app = None
    layout._resolve_app = lambda v: ("weather", "Weather") if v == 10 else (None, None)

    event = Event(event_type="input.switch.changed", payload={"new_value": 10})
    await layout._on_switch_changed(event)

    assert layout._switch_value == 10
    assert layout._app_display_name == "Weather"


@pytest.mark.asyncio
async def test_on_app_started_uses_display_name():
    layout = BossLayout.__new__(BossLayout)
    layout._app_display_name = "—"
    layout._switch_value = 0
    layout._lbl_switch = None
    layout._lbl_app = None
    layout._resolve_app = _null_resolver

    event = Event(
        event_type="system.app.started",
        payload={"app_name": "hello", "display_name": "Hello World"},
    )
    await layout._on_app_started(event)

    assert layout._app_display_name == "Hello World"


@pytest.mark.asyncio
async def test_on_app_started_falls_back_to_app_name():
    layout = BossLayout.__new__(BossLayout)
    layout._app_display_name = "—"
    layout._switch_value = 0
    layout._lbl_switch = None
    layout._lbl_app = None
    layout._resolve_app = _null_resolver

    event = Event(
        event_type="system.app.started",
        payload={"app_name": "hello"},
    )
    await layout._on_app_started(event)

    assert layout._app_display_name == "hello"


@pytest.mark.asyncio
async def test_on_app_finished_resolves_idle_name():
    layout = BossLayout.__new__(BossLayout)
    layout._switch_value = 3
    layout._app_display_name = "Running App"
    layout._lbl_switch = None
    layout._lbl_app = None
    layout._resolve_app = lambda v: ("clock", "Clock") if v == 3 else (None, None)

    event = Event(
        event_type="system.app.finished",
        payload={"app_name": "running_app"},
    )
    await layout._on_app_finished(event)

    assert layout._app_display_name == "Clock"
