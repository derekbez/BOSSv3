"""Tests for the AppRunner."""

import asyncio
import threading

import pytest

from boss.core.app_runner import AppRunner
from boss.core.event_bus import EventBus
from boss.core.models.manifest import AppManifest
from boss.core.app_api import AppAPI
from boss.core.models.config import BossConfig
from tests.helpers.app_scaffold import create_app
from tests.helpers.runtime import wait_for


# Minimal stub for ScreenInterface / LedInterface used by AppAPI.
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


class TestAppRunner:
    async def test_run_simple_app(self, bus, tmp_path):
        app_dir = create_app(tmp_path, "simple", code=(
            "def run(stop_event, api):\n"
            "    api.log_info('hello')\n"
            "    stop_event.wait(0.1)\n"
        ))
        manifest = AppManifest(name="Simple")
        api = _make_api(bus, "simple", app_dir, manifest)
        runner = AppRunner(bus)

        runner.run_app("simple", app_dir, manifest, api)
        await wait_for(lambda: not runner.is_running, timeout=3.0)
        assert not runner.is_running

    async def test_stop_running_app(self, bus, tmp_path):
        app_dir = create_app(tmp_path, "long", code=(
            "def run(stop_event, api):\n"
            "    stop_event.wait(60)\n"
        ))
        manifest = AppManifest(name="Long")
        api = _make_api(bus, "long", app_dir, manifest)
        runner = AppRunner(bus)

        runner.run_app("long", app_dir, manifest, api)
        await asyncio.sleep(0.1)
        assert runner.is_running

        runner.stop(timeout=2.0)
        await asyncio.sleep(0.2)
        assert not runner.is_running

    async def test_app_error_published(self, bus, tmp_path):
        app_dir = create_app(tmp_path, "crash", code=(
            "def run(stop_event, api):\n"
            "    raise RuntimeError('oops')\n"
        ))
        manifest = AppManifest(name="Crash")
        api = _make_api(bus, "crash", app_dir, manifest)
        errors: list[dict] = []

        async def on_error(event):
            errors.append(event.payload)

        bus.subscribe("system.app.error", on_error)
        runner = AppRunner(bus)
        runner.run_app("crash", app_dir, manifest, api)

        await wait_for(lambda: len(errors) > 0, timeout=3.0)
        assert errors[0]["app_name"] == "crash"
        assert "oops" in errors[0]["error"]
