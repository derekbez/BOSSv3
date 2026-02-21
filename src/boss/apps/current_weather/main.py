"""Current Weather — Open-Meteo free API (no key required).

Displays current conditions + next 8 hours compact forecast.
Green = manual refresh.  Requires global location.
"""

from __future__ import annotations

import time
from threading import Event
from typing import Any

from boss.apps._lib.http_helpers import fetch_json

API_URL = "https://api.open-meteo.com/v1/forecast"


def _fetch(lat: float, lon: float, timeout: float) -> dict:
    return fetch_json(
        API_URL,
        params={
            "latitude": str(lat),
            "longitude": str(lon),
            "current_weather": "true",
            "hourly": "temperature_2m,relativehumidity_2m,precipitation,cloudcover,windspeed_10m",
            "timezone": "auto",
            "forecast_days": "1",
        },
        timeout=timeout,
    )


def _format_current(data: dict) -> str:
    cw = data.get("current_weather", {})
    temp = cw.get("temperature", "?")
    wind = cw.get("windspeed", "?")
    return f"Temp: {temp}°C   Wind: {wind} km/h"


def _format_next_hours(data: dict, hours: int = 8) -> str:
    hourly = data.get("hourly", {})
    times = hourly.get("time", [])
    temps = hourly.get("temperature_2m", [])
    humids = hourly.get("relativehumidity_2m", [])
    clouds = hourly.get("cloudcover", [])
    precips = hourly.get("precipitation", [])
    winds = hourly.get("windspeed_10m", [])

    # Find current hour index
    import datetime
    now_str = datetime.datetime.now().strftime("%Y-%m-%dT%H")
    start = 0
    for i, t in enumerate(times):
        if t.startswith(now_str):
            start = i
            break

    lines: list[str] = ["HH  T°  H%  C%  Pmm  Wk"]
    for i in range(start, min(start + hours, len(times))):
        hh = times[i][11:13] if len(times[i]) > 12 else "?"
        t = temps[i] if i < len(temps) else "?"
        h = humids[i] if i < len(humids) else "?"
        c = clouds[i] if i < len(clouds) else "?"
        p = precips[i] if i < len(precips) else 0
        w = winds[i] if i < len(winds) else "?"
        lines.append(f"{hh}  {t:>4}  {h:>3}  {c:>3}  {p:>4}  {w:>4}")
    return "\n".join(lines)


def run(stop_event: Event, api: Any) -> None:
    cfg = api.get_app_config()
    refresh = float(cfg.get("refresh_seconds", 60))
    timeout = float(cfg.get("request_timeout_seconds", 4))
    loc = api.get_global_location()
    lat, lon = loc["lat"], loc["lon"]
    title = "Weather"
    last_fetch = 0.0

    def _show() -> None:
        try:
            data = _fetch(lat, lon, timeout)
            current = _format_current(data)
            forecast = _format_next_hours(data)
            api.screen.clear()
            api.screen.display_text(
                f"{title}\n\n{current}\n\n{forecast}", font_size=16, align="left",
            )
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
