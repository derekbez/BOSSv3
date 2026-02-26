"""Name That Animal — random animal from Zoo Animal API with local fallback.

Green = refresh.  Falls back to ``assets/animals_fallback.json`` if the API
is unreachable (Heroku cold-start / offline).
"""

from __future__ import annotations

import json
import random
import time
import threading
from typing import TYPE_CHECKING, Any

from boss.apps._lib.http_helpers import fetch_json

API_URL = "https://zoo-animal-api.herokuapp.com/animals/rand"


def _format_animal(data: dict) -> str:
    """Format an animal dict (from API or fallback) into display lines."""
    name = data.get("name", "?")
    animal_type = data.get("animal_type", "")
    diet = data.get("diet", "")
    habitat = data.get("habitat", "")
    parts = [name]
    if animal_type:
        parts.append(f"Type: {animal_type}")
    if diet:
        parts.append(f"Diet: {diet}")
    if habitat:
        parts.append(f"Habitat: {habitat}")
    return "\n".join(parts)


def _load_fallback(api: "AppAPI") -> list[dict]:
    """Load the local fallback animal list."""
    try:
        path = api.get_asset_path("animals_fallback.json")
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


if TYPE_CHECKING:
    from boss.core.app_api import AppAPI


def run(stop_event: threading.Event, api: "AppAPI") -> None:
    cfg = api.get_app_config()
    refresh = float(cfg.get("refresh_seconds", 1800))
    timeout = float(cfg.get("request_timeout_seconds", 6))
    title = "Animal Fact"
    last_fetch = 0.0
    fallback: list[dict] = []

    def _show() -> None:
        nonlocal fallback
        try:
            data = fetch_json(API_URL, timeout=timeout)
            info = _format_animal(data)
            api.screen.clear()
            api.screen.display_text(f"{title}\n\n{info}", align="left")
        except Exception:
            # API failed — use local fallback
            if not fallback:
                fallback = _load_fallback(api)
            if fallback:
                api.log_info("Zoo Animal API unreachable, using local fallback")
                data = random.choice(fallback)
                info = _format_animal(data)
                api.screen.clear()
                api.screen.display_text(f"{title} (offline)\n\n{info}", align="left")
            else:
                api.screen.clear()
                api.screen.display_text(f"{title}\n\n(API offline, no fallback data)", align="left")

    def on_button(event: Any) -> None:
        nonlocal last_fetch
        if event.payload.get("button") == "green":
            last_fetch = time.time()
            _show()

    api.hardware.set_led("green", True)
    sub_id = api.event_bus.subscribe("input.button.pressed", on_button)
    try:
        _show()
        last_fetch = time.time()
        while not stop_event.is_set():
            if time.time() - last_fetch >= refresh:
                last_fetch = time.time()
                _show()
            stop_event.wait(0.25)
    finally:
        api.event_bus.unsubscribe(sub_id)
        api.hardware.set_led("green", False)
