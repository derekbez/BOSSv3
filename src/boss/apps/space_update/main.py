"""Space Update — NASA APOD or Mars Curiosity with mode toggle.

Yellow = APOD mode, Green = refresh current, Blue = Mars mode.
"""

from __future__ import annotations

import time
import threading
from typing import TYPE_CHECKING, Any

from boss.apps._lib.http_helpers import fetch_json

APOD_URL = "https://api.nasa.gov/planetary/apod"
MARS_URL = "https://api.nasa.gov/mars-photos/api/v1/rovers/curiosity/latest_photos"


def _fetch_apod(api_key: str, timeout: float) -> str:
    data = fetch_json(APOD_URL, params={"api_key": api_key}, timeout=timeout)
    title = data.get("title", "?")
    explanation = data.get("explanation", "")
    date_str = data.get("date", "")
    snippet = explanation[:200] + "…" if len(explanation) > 200 else explanation
    return f"NASA APOD ({date_str})\n\n{title}\n\n{snippet}"


def _fetch_mars(api_key: str, timeout: float) -> str:
    data = fetch_json(MARS_URL, params={"api_key": api_key}, timeout=timeout)
    photos = data.get("latest_photos", [])
    if not photos:
        return "Mars Curiosity\n\n(no recent photos)"
    p = photos[0]
    camera = p.get("camera", {}).get("full_name", "?")
    earth_date = p.get("earth_date", "?")
    sol = p.get("sol", "?")
    return f"Mars Curiosity\n\nCamera: {camera}\nDate: {earth_date}\nSol: {sol}\nPhotos: {len(photos)}"


if TYPE_CHECKING:
    from boss.core.app_api import AppAPI


def run(stop_event: threading.Event, api: "AppAPI") -> None:
    cfg = api.get_app_config()
    refresh = float(cfg.get("refresh_seconds", 21600))
    timeout = float(cfg.get("request_timeout_seconds", 6))
    api_key = api.get_secret("BOSS_APP_NASA_API_KEY")
    last_fetch = 0.0
    mode = "apod"  # "apod" or "mars"

    def _update_leds() -> None:
        api.hardware.set_led("yellow", mode == "apod")
        api.hardware.set_led("blue", mode == "mars")

    def _show() -> None:
        if not api_key:
            raise RuntimeError("Missing secret: BOSS_APP_NASA_API_KEY")
        try:
            if mode == "apod":
                text = _fetch_apod(api_key, timeout)
            else:
                text = _fetch_mars(api_key, timeout)
            api.screen.clear()
            api.screen.display_text(
                f"{text}\n\n[YEL] APOD  [GRN] Refresh  [BLU] Mars",
                font_size=16,
                align="left",
            )
        except Exception as exc:
            api.screen.clear()
            api.screen.display_text(f"Space\n\nErr: {exc}", align="left")

    def on_button(event: Any) -> None:
        nonlocal last_fetch, mode
        btn = event.payload.get("button")
        if btn == "green":
            last_fetch = time.time()
            _show()
        elif btn == "yellow":
            mode = "apod"
            _update_leds()
            last_fetch = time.time()
            _show()
        elif btn == "blue":
            mode = "mars"
            _update_leds()
            last_fetch = time.time()
            _show()

    api.hardware.set_led("green", True)
    _update_leds()
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
        api.hardware.set_led("yellow", False)
        api.hardware.set_led("blue", False)
