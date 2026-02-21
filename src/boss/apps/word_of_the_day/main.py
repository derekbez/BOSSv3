"""Word of the Day — Wordnik API.  Green = refresh."""

from __future__ import annotations

import time
from threading import Event
from typing import Any

from boss.apps._lib.http_helpers import fetch_json

API_URL = "https://api.wordnik.com/v4/words.json/wordOfTheDay"


def _fetch(api_key: str, timeout: float) -> str:
    if not api_key:
        return "(no Wordnik API key set)"
    data = fetch_json(
        API_URL,
        params={"api_key": api_key},
        timeout=timeout,
    )
    word = data.get("word", "?")
    definitions = data.get("definitions", [])
    defn = definitions[0].get("text", "") if definitions else ""
    examples = data.get("examples", [])
    example = examples[0].get("text", "") if examples else ""
    parts = [word]
    if defn:
        parts.append(f"\n{defn}")
    if example:
        parts.append(f'\nExample: "{example}"')
    return "\n".join(parts)


def run(stop_event: Event, api: Any) -> None:
    cfg = api.get_app_config()
    refresh = float(cfg.get("refresh_seconds", 43200))
    timeout = float(cfg.get("request_timeout_seconds", 6))
    api_key = cfg.get("api_key") or api.get_secret("BOSS_APP_WORDNIK_API_KEY")
    title = "Word of the Day"
    last_fetch = 0.0

    def _show() -> None:
        try:
            text = _fetch(api_key, timeout)
            api.screen.clear()
            api.screen.display_text(f"{title}\n\n{text}", align="left")
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
            stop_event.wait(0.5)
    finally:
        api.event_bus.unsubscribe(sub_id)
        api.hardware.set_led("green", False)
