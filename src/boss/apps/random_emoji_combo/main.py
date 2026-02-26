"""Random Emoji Combo — picks random emojis from local asset.  Green = reshuffle."""

from __future__ import annotations

import json
import random
import time
import threading
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from boss.core.app_api import AppAPI


def run(stop_event: threading.Event, api: "AppAPI") -> None:
    cfg = api.get_app_config()
    min_n = int(cfg.get("min", 2))
    max_n = int(cfg.get("max", 5))
    shuffle_sec = float(cfg.get("shuffle_seconds", 30))

    # Load emojis
    emojis: list[str] = []
    try:
        path = api.get_asset_path("emoji.json")
        with open(path, encoding="utf-8") as f:
            emojis = json.load(f)
        if not isinstance(emojis, list):
            emojis = list(emojis)
    except Exception as exc:
        api.log_error(f"Failed loading emoji.json: {exc}")
        emojis = ["😀", "🎉", "🚀", "🌟", "🎲"]

    last_shuffle = 0.0

    def _show() -> None:
        n = random.randint(min_n, max_n)
        combo = " ".join(random.choices(emojis, k=n))
        api.screen.clear()
        api.screen.display_text(f"Emoji Combo\n\n{combo}", font_size=48, align="center")

    def on_button(event: Any) -> None:
        nonlocal last_shuffle
        if event.payload.get("button") == "green":
            last_shuffle = time.time()
            _show()

    api.hardware.set_led("green", True)
    sub_id = api.event_bus.subscribe("input.button.pressed", on_button)
    try:
        _show()
        last_shuffle = time.time()
        while not stop_event.is_set():
            if time.time() - last_shuffle >= shuffle_sec:
                last_shuffle = time.time()
                _show()
            stop_event.wait(0.5)
    finally:
        api.event_bus.unsubscribe(sub_id)
        api.hardware.set_led("green", False)
