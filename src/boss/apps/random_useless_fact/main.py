"""Random Useless Fact — uselessfacts.jsph.pl.  Green = refresh."""

from __future__ import annotations

import time
from threading import Event
from typing import Any

from boss.apps._lib.http_helpers import fetch_json

API_URL = "https://uselessfacts.jsph.pl/random.json?language=en"


def _fetch(timeout: float) -> str:
    data = fetch_json(API_URL, timeout=timeout)
    return (data.get("text") or "(no fact)").strip()


def run(stop_event: Event, api: Any) -> None:
    cfg = api.get_app_config()
    refresh = float(cfg.get("refresh_seconds", 45))
    timeout = float(cfg.get("request_timeout_seconds", 6))
    title = "Useless Fact"
    last_fetch = 0.0

    def _show() -> None:
        try:
            fact = _fetch(timeout)
            api.screen.clear()
            api.screen.display_text(f"{title}\n\n{fact}", align="left")
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
