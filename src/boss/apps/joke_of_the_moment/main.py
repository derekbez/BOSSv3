"""Joke of the Moment — JokeAPI v2.  Green = reveal punchline / new joke."""

from __future__ import annotations

import time
import threading
from typing import TYPE_CHECKING, Any

from boss.apps._lib.http_helpers import fetch_json

API_URL = "https://v2.jokeapi.dev/joke/{category}"


def _fetch(category: str, joke_type: str, blacklist: list[str], timeout: float) -> dict:
    flags = ",".join(blacklist) if blacklist else ""
    url = API_URL.format(category=category)
    params: dict[str, str] = {"type": joke_type}
    if flags:
        params["blacklistFlags"] = flags
    return fetch_json(url, params=params, timeout=timeout)


if TYPE_CHECKING:
    from boss.core.app_api import AppAPI


def run(stop_event: threading.Event, api: "AppAPI") -> None:
    cfg = api.get_app_config()
    category = cfg.get("category", "Any")
    joke_type = cfg.get("type", "single,twopart")
    blacklist = cfg.get("blacklistFlags", ["nsfw", "religious", "political", "racist", "sexist"])
    refresh = float(cfg.get("refresh_seconds", 600))
    timeout = float(cfg.get("request_timeout_seconds", 6))
    title = "Joke"
    last_fetch = 0.0

    # State for two-part jokes
    pending_punchline: list[str | None] = [None]  # mutable container for closure

    def _show_new() -> None:
        pending_punchline[0] = None
        try:
            data = _fetch(category, joke_type, blacklist, timeout)
            if data.get("type") == "twopart":
                setup = data.get("setup", "?")
                pending_punchline[0] = data.get("delivery", "")
                api.screen.clear()
                api.screen.display_text(
                    f"{title}\n\n{setup}\n\n[GREEN] for punchline…",
                    align="left",
                )
            else:
                joke = data.get("joke", "(no joke)")
                api.screen.clear()
                api.screen.display_text(f"{title}\n\n{joke}", align="left")
        except Exception as exc:
            api.screen.clear()
            api.screen.display_text(f"{title}\n\nErr: {exc}", align="left")

    def on_button(event: Any) -> None:
        nonlocal last_fetch
        if event.payload.get("button") != "green":
            return
        if pending_punchline[0] is not None:
            # Reveal punchline
            api.screen.clear()
            api.screen.display_text(f"{title}\n\n{pending_punchline[0]}", align="left")
            pending_punchline[0] = None
        else:
            last_fetch = time.time()
            _show_new()

    api.hardware.set_led("green", True)
    sub_id = api.event_bus.subscribe("input.button.pressed", on_button)
    try:
        _show_new()
        last_fetch = time.time()
        while not stop_event.is_set():
            if pending_punchline[0] is None and time.time() - last_fetch >= refresh:
                last_fetch = time.time()
                _show_new()
            stop_event.wait(0.25)
    finally:
        api.event_bus.unsubscribe(sub_id)
        api.hardware.set_led("green", False)
