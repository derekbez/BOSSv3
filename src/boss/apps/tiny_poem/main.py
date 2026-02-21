"""Tiny Poem — random poem from Poemist API.  Green = new poem."""

from __future__ import annotations

import textwrap
import time
from threading import Event
from typing import Any

from boss.apps._lib.http_helpers import fetch_json

API_URL = "https://www.poemist.com/api/v1/randompoems"


def _fetch(timeout: float) -> str:
    data = fetch_json(API_URL, timeout=timeout)
    if not data or not isinstance(data, list):
        return "(no poem returned)"
    poem = data[0]
    title = poem.get("title", "Untitled")
    content = poem.get("content", "").strip()
    author = poem.get("poet", {}).get("name", "Unknown")
    # Wrap long lines for screen readability
    wrapped = "\n".join(textwrap.wrap(content, width=80)) if content else "(empty)"
    return f"{title}\n\n{wrapped}\n\n— {author}"


def run(stop_event: Event, api: Any) -> None:
    cfg = api.get_app_config()
    refresh = float(cfg.get("refresh_seconds", 10800))
    timeout = float(cfg.get("request_timeout_seconds", 6))
    title = "Tiny Poem"
    last_fetch = 0.0

    def _show() -> None:
        try:
            text = _fetch(timeout)
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
