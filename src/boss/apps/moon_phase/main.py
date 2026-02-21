"""Moon Phase — ipgeolocation.io astronomy endpoint.  Green = refresh."""

from __future__ import annotations

import time
from threading import Event
from typing import Any

from boss.apps._lib.http_helpers import fetch_json

API_URL = "https://api.ipgeolocation.io/astronomy"


def _fetch(lat: float, lon: float, api_key: str, timeout: float) -> str:
    if not api_key:
        return "(no ipgeolocation API key set)"
    data = fetch_json(
        API_URL,
        params={"apiKey": api_key, "lat": str(lat), "long": str(lon)},
        timeout=timeout,
    )
    phase = data.get("moon_phase", "?")
    illum = data.get("moon_illumination", "?")
    moonrise = data.get("moonrise", "?")
    moonset = data.get("moonset", "?")
    sunrise = data.get("sunrise", "?")
    sunset = data.get("sunset", "?")
    return (
        f"Phase: {phase}\n"
        f"Illumination: {illum}%\n\n"
        f"Moonrise: {moonrise}\n"
        f"Moonset:  {moonset}\n"
        f"Sunrise:  {sunrise}\n"
        f"Sunset:   {sunset}"
    )


def run(stop_event: Event, api: Any) -> None:
    cfg = api.get_app_config()
    refresh = float(cfg.get("refresh_seconds", 21600))
    timeout = float(cfg.get("request_timeout_seconds", 6))
    api_key = cfg.get("api_key") or api.get_secret("BOSS_APP_IPGEO_API_KEY")
    loc = api.get_global_location()
    lat, lon = loc["lat"], loc["lon"]
    title = "Moon Phase"
    last_fetch = 0.0

    def _show() -> None:
        try:
            text = _fetch(lat, lon, api_key, timeout)
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
