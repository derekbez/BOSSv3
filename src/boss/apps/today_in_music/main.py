"""Today in Music — top track for a genre tag via Last.fm.  Green = refresh."""

from __future__ import annotations

import time
import threading
from typing import TYPE_CHECKING, Any

from boss.apps._lib.http_helpers import fetch_json

API_URL = "https://ws.audioscrobbler.com/2.0/"


def _fetch(tag: str, api_key: str, timeout: float) -> str:
    if not api_key:
        return "(no Last.fm API key set)"
    data = fetch_json(
        API_URL,
        params={
            "method": "tag.gettoptracks",
            "tag": tag,
            "api_key": api_key,
            "format": "json",
            "limit": "5",
        },
        timeout=timeout,
    )
    tracks = data.get("tracks", {}).get("track", [])
    if not tracks:
        return "(no tracks found)"
    lines: list[str] = []
    for t in tracks[:5]:
        artist = t.get("artist", {}).get("name", "?")
        name = t.get("name", "?")
        lines.append(f"{artist} — {name}")
    return "\n".join(lines)


if TYPE_CHECKING:
    from boss.core.app_api import AppAPI


def run(stop_event: threading.Event, api: "AppAPI") -> None:
    cfg = api.get_app_config()
    tag = cfg.get("tag", "rock")
    refresh = float(cfg.get("refresh_seconds", 3600))
    timeout = float(cfg.get("request_timeout_seconds", 6))
    api_key = cfg.get("api_key") or api.get_secret("BOSS_APP_LASTFM_API_KEY")
    title = f"Music: {tag}"
    last_fetch = 0.0

    def _show() -> None:
        try:
            text = _fetch(tag, api_key, timeout)
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
