"""ISS Tracker — current ISS position + crew count.

Green = refresh.
"""

from __future__ import annotations

import math
import threading
import time
from typing import TYPE_CHECKING, Any

from boss.apps._lib.http_helpers import fetch_json

ISS_POS_URL = "https://api.wheretheiss.at/v1/satellites/25544"
ASTROS_URL = "http://api.open-notify.org/astros.json"


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    return 2.0 * r * math.asin(math.sqrt(a))


def _fetch(timeout: float) -> tuple[float, float, float, int | None]:
    pos = fetch_json(ISS_POS_URL, timeout=timeout)
    lat = float(pos.get("latitude", 0.0))
    lon = float(pos.get("longitude", 0.0))
    alt_km = float(pos.get("altitude", 0.0))

    crew_count: int | None = None
    try:
        astros = fetch_json(ASTROS_URL, timeout=timeout)
        people = astros.get("people", [])
        if isinstance(people, list):
            crew_count = sum(1 for p in people if str(p.get("craft", "")).strip().upper() == "ISS")
    except Exception:
        crew_count = None

    return lat, lon, alt_km, crew_count


if TYPE_CHECKING:
    from boss.core.app_api import AppAPI


def run(stop_event: threading.Event, api: "AppAPI") -> None:
    cfg = api.get_app_config()
    refresh = float(cfg.get("refresh_seconds", 30))
    timeout = float(cfg.get("request_timeout_seconds", 6))
    title = "ISS Tracker"
    last_fetch = 0.0

    loc = api.get_global_location()
    user_lat = float(loc["lat"])
    user_lon = float(loc["lon"])

    def _show() -> None:
        try:
            iss_lat, iss_lon, alt_km, crew_count = _fetch(timeout)
            dist_km = _haversine_km(user_lat, user_lon, iss_lat, iss_lon)
            crew = str(crew_count) if crew_count is not None else "?"
            api.screen.clear()
            api.screen.display_text(
                (
                    f"{title}\n\n"
                    f"ISS Lat/Lon: {iss_lat:.2f}, {iss_lon:.2f}\n"
                    f"Altitude: {alt_km:.0f} km\n"
                    f"Distance from you: {dist_km:.0f} km\n"
                    f"Crew on ISS: {crew}"
                ),
                align="left",
                font_size=18,
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
            stop_event.wait(0.25)
    finally:
        api.event_bus.unsubscribe(sub_id)
        api.hardware.set_led("green", False)
