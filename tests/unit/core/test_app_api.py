"""Tests for the AppAPI."""

import pytest

from boss.core.app_api import AppAPI
from boss.core.event_bus import EventBus
from boss.core.models.config import BossConfig
from boss.core.models.manifest import AppManifest


class _StubScreen:
    def display_text(self, text, **kw): pass
    def display_html(self, html): pass
    def display_image(self, path): pass
    def display_markdown(self, md): pass
    def clear(self): pass


class _StubLeds:
    def __init__(self):
        self.calls: list[tuple] = []
    def set_led(self, color, on):
        self.calls.append((color, on))
    def get_state(self, color): return False
    def all_off(self): pass


@pytest.fixture
async def bus():
    b = EventBus(queue_size=100)
    await b.start()
    yield b
    await b.stop()


@pytest.fixture
def api(bus, tmp_path):
    manifest = AppManifest(
        name="Test App",
        config={"refresh": 30, "units": "metric"},
    )
    app_dir = tmp_path / "test_app"
    app_dir.mkdir()
    return AppAPI(
        app_name="test_app",
        app_dir=app_dir,
        manifest=manifest,
        event_bus=bus,
        screen=_StubScreen(),
        leds=_StubLeds(),
        config=BossConfig(),
    )


class TestAppAPIConfig:
    def test_get_app_config(self, api: AppAPI):
        cfg = api.get_app_config()
        assert cfg["refresh"] == 30
        assert cfg["units"] == "metric"

    def test_get_config_value(self, api: AppAPI):
        assert api.get_config_value("refresh") == 30
        assert api.get_config_value("missing", "default") == "default"

    def test_get_global_location(self, api: AppAPI):
        loc = api.get_global_location()
        assert "lat" in loc
        assert "lon" in loc


class TestAppAPIPaths:
    def test_get_app_path(self, api: AppAPI, tmp_path):
        assert api.get_app_path() == tmp_path / "test_app"

    def test_get_asset_path(self, api: AppAPI, tmp_path):
        assert api.get_asset_path("logo.png") == tmp_path / "test_app" / "assets" / "logo.png"


class TestAppAPIScopedEventBus:
    async def test_cleanup_unsubscribes_all(self, api: AppAPI, bus):
        call_count = 0

        async def handler(_e):
            nonlocal call_count
            call_count += 1

        api.event_bus.subscribe("test.evt", handler)
        api.event_bus.subscribe("test.evt2", handler)
        api._cleanup()

        # After cleanup, publishing should not reach the handler.
        import asyncio
        await bus.publish("test.evt")
        await bus.publish("test.evt2")
        await asyncio.sleep(0.1)
        assert call_count == 0


class TestAppAPILogging:
    def test_log_methods_exist(self, api: AppAPI):
        # Should not raise.
        api.log_debug("debug msg")
        api.log_info("info msg")
        api.log_warning("warn msg")
        api.log_error("error msg")
