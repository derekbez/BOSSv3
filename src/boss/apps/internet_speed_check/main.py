"""Internet Speed Check — placeholder with simulated values.  Green = retest."""

from __future__ import annotations

import random
import time
import threading
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from boss.core.app_api import AppAPI


def run(stop_event: threading.Event, api: "AppAPI") -> None:
    cfg = api.get_app_config()
    refresh = float(cfg.get("refresh_seconds", 1800))
    title = "Net Speed"
    last_fetch = 0.0

    def _show() -> None:
        down = random.uniform(20, 120)
        up = random.uniform(10, 40)
        ping = random.uniform(10, 60)
        api.screen.clear()
        api.screen.display_text(
            f"{title}\n\nDown {down:.1f} Mbps\nUp   {up:.1f} Mbps\nPing {ping:.0f} ms",
            align="left",
        )

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
            stop_event.wait(0.5)
    finally:
        api.event_bus.unsubscribe(sub_id)
        api.hardware.set_led("green", False)
