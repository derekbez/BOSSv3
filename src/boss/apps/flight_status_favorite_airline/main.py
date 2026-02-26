"""Flight Status Favourite Airline — Aviationstack.  Green = refresh."""

from __future__ import annotations

import time
import threading
from typing import TYPE_CHECKING, Any

from boss.apps._lib.http_helpers import fetch_json

API_URL = "https://api.aviationstack.com/v1/flights"


def _fetch(api_key: str, airline_iata: str, timeout: float) -> str:
    if not api_key:
        return "(no Aviationstack API key set)"
    data = fetch_json(
        API_URL,
        params={
            "access_key": api_key,
            "airline_iata": airline_iata,
            "limit": "6",
        },
        timeout=timeout,
    )
    flights = data.get("data", [])
    if not flights:
        return f"(no flights found for {airline_iata})"
    lines: list[str] = []
    for f in flights[:6]:
        code = f.get("flight", {}).get("iata", "?")
        status = f.get("flight_status", "")
        dep = f.get("departure", {}).get("scheduled", "")
        dep_time = dep[11:16] if len(dep) > 15 else dep
        lines.append(f"{code:8s} {dep_time}  {status}")
    return "\n".join(lines)


if TYPE_CHECKING:
    from boss.core.app_api import AppAPI


def run(stop_event: threading.Event, api: "AppAPI") -> None:
    cfg = api.get_app_config()
    iata = cfg.get("iata", "BA")
    refresh = float(cfg.get("refresh_seconds", 600))
    timeout = float(cfg.get("request_timeout_seconds", 6))
    api_key = cfg.get("api_key") or api.get_secret("BOSS_APP_AVIATIONSTACK_API_KEY")
    title = f"Flights: {iata}"
    last_fetch = 0.0

    def _show() -> None:
        try:
            text = _fetch(api_key, iata, timeout)
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
