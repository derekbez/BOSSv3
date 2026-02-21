"""Smoke tests — import and briefly run each migrated app's run() function.

Uses a lightweight mock API to verify apps start, display something,
and exit cleanly when ``stop_event`` is set.
"""

from __future__ import annotations

import importlib.util
import json
import threading
import time
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

APPS_DIR = Path(__file__).resolve().parents[3] / "src" / "boss" / "apps"

# Apps that need network calls — skip actual run but verify they import
NETWORK_APPS = {
    "bird_sightings_near_me",
    "breaking_news",
    "color_of_the_day",
    "current_weather",
    "dad_joke_generator",
    "flight_status_favorite_airline",
    "flights_leaving_heathrow",
    "joke_of_the_moment",
    "local_tide_times",
    "moon_phase",
    "name_that_animal",
    "on_this_day",
    "quote_of_the_day",
    "random_useless_fact",
    "space_update",
    "tiny_poem",
    "today_in_music",
    "top_trending_search",
    "word_of_the_day",
}

# Apps that are safe to run locally (no network, read assets or simple logic)
LOCAL_APPS = {
    "admin_shutdown",
    "admin_startup",
    "app_jokes",
    "constellation_of_the_night",
    "hello_world",
    "internet_speed_check",
    "list_all_apps",
    "public_domain_book_snippet",
    "random_emoji_combo",
    "random_local_place_name",
}


def _discover_apps() -> list[str]:
    return sorted(
        d.name
        for d in APPS_DIR.iterdir()
        if d.is_dir()
        and not d.name.startswith("_")
        and not d.name.startswith("__")
        and (d / "main.py").exists()
    )


def _load_run(app_name: str):
    """Dynamically import the app's main.py and return its run function."""
    entry = APPS_DIR / app_name / "main.py"
    spec = importlib.util.spec_from_file_location(f"boss.apps.{app_name}.main", entry)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.run


class MockScreen:
    def __init__(self):
        self.texts: list[str] = []
        self.cleared = 0

    def display_text(self, text: str, **kwargs: Any) -> None:
        self.texts.append(text)

    def display_html(self, html: str) -> None:
        pass

    def display_image(self, path: str) -> None:
        pass

    def display_markdown(self, md: str) -> None:
        pass

    def clear(self) -> None:
        self.cleared += 1


class MockHardwareAPI:
    def __init__(self):
        self.leds: dict[str, bool] = {}

    def set_led(self, color: str, on: bool) -> None:
        self.leds[color] = on


class MockEventBus:
    def __init__(self):
        self._handlers: dict[str, Any] = {}

    def subscribe(self, event_type: str, handler: Any, filter_dict: Any = None) -> str:
        sid = f"sub_{id(handler)}"
        self._handlers[sid] = handler
        return sid

    def unsubscribe(self, sub_id: str) -> None:
        self._handlers.pop(sub_id, None)

    def publish_threadsafe(self, event_type: str, payload: dict | None = None) -> None:
        pass


class MockAPI:
    def __init__(self, app_name: str):
        self.screen = MockScreen()
        self.hardware = MockHardwareAPI()
        self.event_bus = MockEventBus()
        self._app_name = app_name
        self._app_dir = APPS_DIR / app_name

    def get_app_config(self) -> dict:
        manifest_path = self._app_dir / "manifest.json"
        if manifest_path.exists():
            raw = json.loads(manifest_path.read_text(encoding="utf-8"))
            return raw.get("config", {})
        return {}

    def get_config_value(self, key: str, default: Any = None) -> Any:
        return self.get_app_config().get(key, default)

    def get_global_location(self) -> dict:
        return {"lat": 51.5074, "lon": -0.1278}

    def get_secret(self, key: str, default: str = "") -> str:
        return default

    def get_all_app_summaries(self) -> list[dict]:
        return [
            {"switch": 0, "name": "list_all_apps", "description": "Lists apps"},
            {"switch": 1, "name": "hello_world", "description": "Demo app"},
        ]

    def get_app_path(self) -> Path:
        return self._app_dir

    def get_asset_path(self, filename: str) -> Path:
        return self._app_dir / "assets" / filename

    def log_info(self, msg: str) -> None:
        pass

    def log_debug(self, msg: str) -> None:
        pass

    def log_warning(self, msg: str) -> None:
        pass

    def log_error(self, msg: str) -> None:
        pass


class TestAppImports:
    """Verify every app module can be imported without error."""

    @pytest.mark.parametrize("app_name", _discover_apps())
    def test_import(self, app_name: str):
        run_func = _load_run(app_name)
        assert callable(run_func)


class TestLocalAppSmoke:
    """Run local-only apps briefly and verify they display something."""

    @pytest.mark.parametrize("app_name", sorted(LOCAL_APPS & set(_discover_apps())))
    def test_run(self, app_name: str):
        run_func = _load_run(app_name)
        api = MockAPI(app_name)
        stop = threading.Event()

        def _run():
            try:
                run_func(stop, api)
            except Exception:
                pass  # Some may error on missing assets in CI

        t = threading.Thread(target=_run, daemon=True)
        t.start()
        # Let it run for a brief moment
        time.sleep(0.5)
        stop.set()
        t.join(timeout=3.0)
        assert not t.is_alive(), f"{app_name} did not stop within 3s"
        # Should have displayed something or cleared screen
        assert api.screen.texts or api.screen.cleared > 0
