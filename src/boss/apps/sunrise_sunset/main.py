"""Sunrise / Sunset — daylight timings for current location.

Green = refresh.
"""

from __future__ import annotations

from datetime import datetime, timezone
import threading
import time
from typing import TYPE_CHECKING, Any

from boss.apps._lib.http_helpers import fetch_json

API_URL = "https://api.sunrise-sunset.org/json"


def _fmt_time(ts: str) -> str:
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.strftime("%H:%M UTC")
    except Exception:
        return ts


def _fmt_duration(seconds: int) -> str:
    minutes = max(0, int(seconds)) // 60
    hours, mins = divmod(minutes, 60)
    return f"{hours}h {mins}m"


def _fetch(lat: float, lon: float, timeout: float) -> dict[str, str]:
    data = fetch_json(
        API_URL,
        params={
            "lat": f"{lat:.6f}",
            "lng": f"{lon:.6f}",
            "formatted": "0",
        },
        timeout=timeout,
    )
    results = data.get("results", {})
    if not results:
        raise RuntimeError("No sunrise/sunset data")

    return {
        "sunrise": _fmt_time(str(results.get("sunrise", "?"))),
        "sunset": _fmt_time(str(results.get("sunset", "?"))),
        "solar_noon": _fmt_time(str(results.get("solar_noon", "?"))),
        "first_light": _fmt_time(str(results.get("civil_twilight_begin", "?"))),
        "last_light": _fmt_time(str(results.get("civil_twilight_end", "?"))),
        "day_length": _fmt_duration(int(results.get("day_length", 0))),
    }


if TYPE_CHECKING:
    from boss.core.app_api import AppAPI


def run(stop_event: threading.Event, api: "AppAPI") -> None:
    cfg = api.get_app_config()
    refresh = float(cfg.get("refresh_seconds", 3600))
    timeout = float(cfg.get("request_timeout_seconds", 6))
    last_fetch = 0.0

    loc = api.get_global_location()
    lat = float(loc["lat"])
    lon = float(loc["lon"])

    def _show() -> None:
        try:
            info = _fetch(lat, lon, timeout)
            api.screen.clear()
            api.screen.display_text(
                (
                    "Sunrise / Sunset\n\n"
                    f"Lat/Lon: {lat:.2f}, {lon:.2f}\n"
                    f"Sunrise: {info['sunrise']}\n"
                    f"Sunset: {info['sunset']}\n"
                    f"Solar noon: {info['solar_noon']}\n"
                    f"First light: {info['first_light']}\n"
                    f"Last light: {info['last_light']}\n"
                    f"Day length: {info['day_length']}"
                ),
                align="left",
                font_size=16,
            )
        except Exception as exc:
            api.screen.clear()
            api.screen.display_text(f"Sunrise / Sunset\n\nErr: {exc}", align="left")

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
