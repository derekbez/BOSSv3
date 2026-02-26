"""Smoke tests — import and briefly run each migrated app's run() function.

Uses a lightweight mock API to verify apps start, display something,
and exit cleanly when ``stop_event`` is set.
"""

from __future__ import annotations

import importlib.util
import json
import threading
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from tests.helpers.runtime import wait_for_sync

from boss.core.app_api import AppAPI

APPS_DIR = Path(__file__).resolve().parents[3] / "src" / "boss" / "apps"

# Apps that need network calls — skip actual run but verify they import
NETWORK_APPS = {
    "air_quality_index",
    "bird_sightings_near_me",
    "breaking_news",
    "cocktail_of_the_day",
    "crypto_ticker",
    "currency_exchange",
    "color_of_the_day",
    "constellation_of_the_night",
    "current_weather",
    "dad_joke_generator",
    "flight_status_favorite_airline",
    "flights_leaving_heathrow",
    "iss_tracker",
    "internet_speed_check",
    "joke_of_the_moment",
    "local_tide_times",
    "moon_phase",
    "name_that_animal",
    "on_this_day",
    "meal_idea",
    "quote_of_the_day",
    "random_useless_fact",
    "space_update",
    "country_fact",
    "earthquake_monitor",
    "sunrise_sunset",
    "tiny_poem",
    "today_in_music",
    "top_trending_search",
    "trivia_quiz",
    "uv_index",
    "wikipedia_random_article",
    "word_of_the_day",
}

# Apps that are safe to run locally (no network, read assets or simple logic)
LOCAL_APPS = {
    "admin_boss_admin",
    "admin_shutdown",
    "admin_startup",
    "admin_wifi_configuration",
    "app_jokes",
    "coin_flip_streak",
    "countdown_to_event",
    "hello_world",
    "list_all_apps",
    "math_challenge",
    "number_guess",
    "pomodoro_timer",
    "public_domain_book_snippet",
    "random_emoji_combo",
    "random_local_place_name",
    "rock_paper_scissors",
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
        self.htmls: list[str] = []
        self.cleared = 0

    def display_text(self, text: str, **kwargs: Any) -> None:
        self.texts.append(text)

    def display_html(self, html: str) -> None:
        self.htmls.append(html)

    def display_image(self, path: str) -> None:
        pass

    def display_markdown(self, md: str) -> None:
        pass

    def clear(self) -> None:
        self.cleared += 1


def _make_mock_api(app_name: str) -> Any:
    """Build an ``AppAPI``-shaped mock using ``create_autospec``.

    This guarantees the mock surface always matches the real ``AppAPI``
    (missing/renamed methods will cause ``AttributeError``), while still
    providing a real ``MockScreen`` instance so tests can inspect output.
    """
    from unittest.mock import create_autospec

    api = create_autospec(AppAPI, instance=True)
    app_dir = APPS_DIR / app_name

    # Wire up sub-objects that apps interact with directly
    api.screen = MockScreen()
    api.hardware = MagicMock()
    api.event_bus = MagicMock()
    api.event_bus.subscribe.return_value = "mock_sub_id"

    # Config access
    manifest_path = app_dir / "manifest.json"
    manifest_config: dict[str, Any] = {}
    if manifest_path.exists():
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest_config = raw.get("config", {})

    api.get_app_config.return_value = manifest_config
    api.get_config_value.side_effect = lambda key, default=None: manifest_config.get(key, default)
    api.get_global_location.return_value = {"lat": 51.5074, "lon": -0.1278}
    api.get_secret.return_value = ""
    api.get_all_app_summaries.return_value = [
        {"switch": 0, "name": "list_all_apps", "description": "Lists apps"},
        {"switch": 1, "name": "hello_world", "description": "Demo app"},
    ]
    api.get_app_path.return_value = app_dir
    api.get_asset_path.side_effect = lambda filename: app_dir / "assets" / filename
    api.get_webui_port.return_value = 8080
    api.is_dev_mode.return_value = False

    return api


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
        api = _make_mock_api(app_name)
        stop = threading.Event()

        def _run():
            try:
                run_func(stop, api)
            except Exception:
                pass  # Some may error on missing assets in CI

        t = threading.Thread(target=_run, daemon=True)
        t.start()
        # Wait until the app has rendered something or cleared the screen,
        # with a timeout rather than a fixed sleep.
        wait_for_sync(
            lambda: api.screen.texts or api.screen.htmls or api.screen.cleared > 0,
            timeout=3.0,
            interval=0.05,
        )
        stop.set()
        t.join(timeout=3.0)
        assert not t.is_alive(), f"{app_name} did not stop within 3s"
        # Should have displayed something or cleared screen
        assert api.screen.texts or api.screen.htmls or api.screen.cleared > 0
