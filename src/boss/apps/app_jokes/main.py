"""App Jokes — static joke display from local JSON.  Yellow = next joke."""

from __future__ import annotations

import json
import random
import threading
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from boss.core.app_api import AppAPI


def run(stop_event: threading.Event, api: "AppAPI") -> None:
    api.log_info("app_jokes starting")
    jokes: list[str] = []
    idx = 0

    # -- load jokes -------------------------------------------------------
    try:
        path = api.get_asset_path("jokes.json")
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        jokes = data.get("jokes", []) or ["(no jokes found)"]
    except Exception as exc:
        api.log_error(f"Failed loading jokes: {exc}")
        jokes = ["(error loading jokes)"]

    shuffle = api.get_config_value("shuffle", True)
    if shuffle:
        random.shuffle(jokes)

    # -- helpers ----------------------------------------------------------
    def _show() -> None:
        if not jokes:
            api.screen.display_text("(no jokes)", align="center")
            return
        api.screen.clear()
        api.screen.display_text(jokes[idx % len(jokes)], align="center")

    def _next() -> None:
        nonlocal idx
        idx = (idx + 1) % max(1, len(jokes))
        _show()

    def on_button(event: Any) -> None:
        if event.payload is None:
            return
        if event.payload.get("button") == "yellow":
            _next()

    # -- main body --------------------------------------------------------
    _show()
    api.hardware.set_led("yellow", True)
    sub_id = api.event_bus.subscribe("input.button.pressed", on_button)

    try:
        while not stop_event.is_set():
            stop_event.wait(0.5)
    finally:
        api.event_bus.unsubscribe(sub_id)
        api.hardware.set_led("yellow", False)
        api.log_info("app_jokes stopping")
