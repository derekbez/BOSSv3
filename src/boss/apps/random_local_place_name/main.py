"""Random Local Place Name — picks from local places.json asset.  Green = reshuffle."""

from __future__ import annotations

import json
import random
import threading
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from boss.core.app_api import AppAPI


def run(stop_event: threading.Event, api: "AppAPI") -> None:
    # Load places
    places: list[str] = []
    try:
        path = api.get_asset_path("places.json")
        with open(path, encoding="utf-8") as f:
            places = json.load(f)
        if not isinstance(places, list):
            places = list(places)
    except Exception as exc:
        api.log_error(f"Failed loading places.json: {exc}")
        places = ["(no places loaded)"]

    def _show() -> None:
        if not places:
            api.screen.clear()
            api.screen.display_text("No places loaded", font_size=28, align="center")
            return
        place = random.choice(places)
        api.screen.clear()
        api.screen.display_text(f"Random Place\n\n{place}", font_size=28, align="center")

    def on_button(event: Any) -> None:
        if event.payload.get("button") == "green":
            _show()

    api.hardware.set_led("green", True)
    sub_id = api.event_bus.subscribe("input.button.pressed", on_button)
    try:
        _show()
        while not stop_event.is_set():
            stop_event.wait(0.5)
    finally:
        api.event_bus.unsubscribe(sub_id)
        api.hardware.set_led("green", False)
