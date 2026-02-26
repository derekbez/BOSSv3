"""Air Quality Index — AQI and pollutant values for current location.

Green = refresh.
"""

from __future__ import annotations

import threading
import time
from typing import TYPE_CHECKING, Any

from boss.apps._lib.http_helpers import fetch_json

API_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"


def _aqi_band(us_aqi: float | None) -> str:
    if us_aqi is None:
        return "Unknown"
    if us_aqi <= 50:
        return "Good"
    if us_aqi <= 100:
        return "Moderate"
    if us_aqi <= 150:
        return "Unhealthy for Sensitive Groups"
    if us_aqi <= 200:
        return "Unhealthy"
    if us_aqi <= 300:
        return "Very Unhealthy"
    return "Hazardous"


def _fetch(lat: float, lon: float, timeout: float) -> dict[str, float | None]:
    data = fetch_json(
        API_URL,
        params={
            "latitude": f"{lat:.6f}",
            "longitude": f"{lon:.6f}",
            "current": "us_aqi,european_aqi,pm2_5,pm10,nitrogen_dioxide",
            "timezone": "auto",
        },
        timeout=timeout,
    )
    current = data.get("current", {})
    return {
        "us_aqi": current.get("us_aqi"),
        "eu_aqi": current.get("european_aqi"),
        "pm25": current.get("pm2_5"),
        "pm10": current.get("pm10"),
        "no2": current.get("nitrogen_dioxide"),
    }


def _fmt(value: float | None, digits: int = 1) -> str:
    if isinstance(value, (int, float)):
        return f"{value:.{digits}f}"
    return "n/a"


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
            values = _fetch(lat, lon, timeout)
            us_aqi = values.get("us_aqi")
            api.screen.clear()
            api.screen.display_text(
                (
                    "Air Quality Index\n\n"
                    f"US AQI: {_fmt(us_aqi, 0)} ({_aqi_band(us_aqi if isinstance(us_aqi, (int, float)) else None)})\n"
                    f"EU AQI: {_fmt(values.get('eu_aqi'), 0)}\n"
                    f"PM2.5: {_fmt(values.get('pm25'))} µg/m³\n"
                    f"PM10: {_fmt(values.get('pm10'))} µg/m³\n"
                    f"NO₂: {_fmt(values.get('no2'))} µg/m³"
                ),
                align="left",
                font_size=16,
            )
        except Exception as exc:
            api.screen.clear()
            api.screen.display_text(f"Air Quality Index\n\nErr: {exc}", align="left")

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
