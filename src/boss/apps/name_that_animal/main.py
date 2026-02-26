"""Name That Animal — random animal from Zoo Animal API.  Green = refresh."""

from __future__ import annotations

import time
import threading
from typing import TYPE_CHECKING, Any

from boss.apps._lib.http_helpers import fetch_json

API_URL = "https://zoo-animal-api.herokuapp.com/animals/rand"


def _fetch(timeout: float) -> str:
    data = fetch_json(API_URL, timeout=timeout)
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


if TYPE_CHECKING:
    from boss.core.app_api import AppAPI


def run(stop_event: threading.Event, api: "AppAPI") -> None:
    cfg = api.get_app_config()
    refresh = float(cfg.get("refresh_seconds", 1800))
    timeout = float(cfg.get("request_timeout_seconds", 6))
    title = "Animal Fact"
    last_fetch = 0.0

    def _show() -> None:
        try:
            info = _fetch(timeout)
            api.screen.clear()
            api.screen.display_text(f"{title}\n\n{info}", align="left")
        except Exception as exc:
            api.screen.clear()
            api.screen.display_text(f"{title}\n\nErr: {exc}", align="left")

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
