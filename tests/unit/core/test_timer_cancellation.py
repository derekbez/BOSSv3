"""Tests for AppRunner timer cancellation (Bug #2).

Ensures the timeout timer is cancelled when an app finishes normally
or when ``stop()`` is called, preventing stale timers from incorrectly
setting ``stop_event`` on subsequent apps.
"""

from __future__ import annotations

import asyncio
import threading

import pytest

from boss.core.app_runner import AppRunner
from boss.core.app_api import AppAPI
from boss.core.event_bus import EventBus
from boss.core.models.config import BossConfig
from boss.core.models.manifest import AppManifest
from tests.helpers.app_scaffold import create_app
from tests.helpers.runtime import wait_for


class _StubScreen:
    def display_text(self, text, **kw): pass
    def display_html(self, html): pass
    def display_image(self, path): pass
    def display_markdown(self, md): pass
    def clear(self): pass


class _StubLeds:
    def set_led(self, color, on): pass
    def get_state(self, color): return False
    def all_off(self): pass


@pytest.fixture
async def bus():
    b = EventBus(queue_size=100)
    await b.start()
    yield b
    await b.stop()


def _make_api(bus, app_name, app_dir, manifest):
    return AppAPI(
        app_name=app_name,
        app_dir=app_dir,
        manifest=manifest,
        event_bus=bus,
        screen=_StubScreen(),
        leds=_StubLeds(),
        config=BossConfig(),
    )


class TestTimerCancellation:
    """Verify the timeout timer is properly cancelled."""

    async def test_timer_cancelled_after_app_finishes(self, bus, tmp_path):
        """Timer should be cancelled when the app completes normally."""
        app_dir = create_app(tmp_path, "quick", code=(
            "def run(stop_event, api):\n"
            "    stop_event.wait(0.1)\n"
        ))
        manifest = AppManifest(name="Quick", timeout_seconds=60)
        api = _make_api(bus, "quick", app_dir, manifest)
        runner = AppRunner(bus)

        runner.run_app("quick", app_dir, manifest, api)
        await wait_for(lambda: not runner.is_running, timeout=3.0)

        # Timer should have been cancelled on completion
        assert runner._timer is None

    async def test_timer_cancelled_on_stop(self, bus, tmp_path):
        """Timer should be cancelled when stop() is called."""
        app_dir = create_app(tmp_path, "long", code=(
            "def run(stop_event, api):\n"
            "    stop_event.wait(60)\n"
        ))
        manifest = AppManifest(name="Long", timeout_seconds=60)
        api = _make_api(bus, "long", app_dir, manifest)
        runner = AppRunner(bus)

        runner.run_app("long", app_dir, manifest, api)
        await asyncio.sleep(0.1)
        assert runner.is_running

        runner.stop(timeout=2.0)
        assert runner._timer is None

    async def test_rapid_relaunch_no_stale_timer(self, bus, tmp_path):
        """Rapidly launching a new app should cancel the previous timer."""
        app_dir = create_app(tmp_path, "wait", code=(
            "def run(stop_event, api):\n"
            "    stop_event.wait(60)\n"
        ))
        manifest = AppManifest(name="Wait", timeout_seconds=60)

        runner = AppRunner(bus)

        # Launch first app
        api1 = _make_api(bus, "wait1", app_dir, manifest)
        runner.run_app("wait1", app_dir, manifest, api1)
        await asyncio.sleep(0.1)
        assert runner.is_running

        # Immediately launch second app (triggers stop on first)
        api2 = _make_api(bus, "wait2", app_dir, manifest)
        runner.run_app("wait2", app_dir, manifest, api2)
        await asyncio.sleep(0.1)

        # The second app's timer should be active, the first's cancelled
        assert runner._timer is not None
        assert runner._app_name == "wait2"

        runner.stop()
        assert runner._timer is None
