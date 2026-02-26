"""UV Index — current UV level and guidance for current location.

Green = refresh.
"""

from __future__ import annotations

import threading
import time
from typing import TYPE_CHECKING, Any

from boss.apps._lib.http_helpers import fetch_json

API_URL = "https://api.open-meteo.com/v1/forecast"


def _uv_band(uv: float | None) -> tuple[str, str]:
    if uv is None:
        return "Unknown", "No guidance available"
    if uv < 3:
        return "Low", "Minimal protection needed"
    if uv < 6:
        return "Moderate", "Use SPF and seek shade at midday"
    if uv < 8:
        return "High", "Reduce midday sun exposure"
    if uv < 11:
        return "Very High", "Extra protection required"
    return "Extreme", "Avoid direct sun; full protection advised"


def _fetch(lat: float, lon: float, timeout: float) -> float | None:
    data = fetch_json(
        API_URL,
        params={
            "latitude": f"{lat:.6f}",
            "longitude": f"{lon:.6f}",
            "current": "uv_index",
            "timezone": "auto",
        },
        timeout=timeout,
    )
    current = data.get("current", {})
    uv = current.get("uv_index")
    return float(uv) if isinstance(uv, (int, float)) else None


if TYPE_CHECKING:
    from boss.core.app_api import AppAPI


def run(stop_event: threading.Event, api: "AppAPI") -> None:
    cfg = api.get_app_config()
    refresh = float(cfg.get("refresh_seconds", 900))
    timeout = float(cfg.get("request_timeout_seconds", 6))
    last_fetch = 0.0

    loc = api.get_global_location()
    lat = float(loc["lat"])
    lon = float(loc["lon"])

    def _show() -> None:
        try:
            uv = _fetch(lat, lon, timeout)
            band, guidance = _uv_band(uv)
            uv_text = f"{uv:.1f}" if isinstance(uv, (int, float)) else "n/a"
            api.screen.clear()
            api.screen.display_text(
                (
                    "UV Index\n\n"
                    f"Current UV: {uv_text}\n"
                    f"Level: {band}\n\n"
                    f"{guidance}"
                ),
                align="left",
                font_size=18,
            )
        except Exception as exc:
            api.screen.clear()
            api.screen.display_text(f"UV Index\n\nErr: {exc}", align="left")

    def on_button(event: Any) -> None:
        nonlocal last_fetch
        payload = event.payload or {}
        if payload.get("button") == "green":
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
