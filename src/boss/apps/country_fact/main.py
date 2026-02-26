"""Country Fact — random country facts from REST Countries.

Green = new country.
"""

from __future__ import annotations

import random
import threading
import time
from typing import TYPE_CHECKING, Any

from boss.apps._lib.http_helpers import fetch_json

API_URL = "https://restcountries.com/v3.1/all"


def _fetch(timeout: float) -> dict:
    countries = fetch_json(
        API_URL,
        params={"fields": "name,capital,population,region,languages,flag"},
        timeout=timeout,
    )
    if not isinstance(countries, list) or not countries:
        raise RuntimeError("No country data")
    return random.choice(countries)


def _format(country: dict) -> str:
    name = country.get("name", {}).get("common", "?")
    flag = country.get("flag", "")
    capital = ", ".join(country.get("capital", []) or []) or "Unknown"
    population = int(country.get("population", 0))
    region = country.get("region", "Unknown")
    languages = ", ".join((country.get("languages", {}) or {}).values()) or "Unknown"

    return (
        f"{flag} {name}\n\n"
        f"Capital: {capital}\n"
        f"Region: {region}\n"
        f"Population: {population:,}\n"
        f"Languages: {languages}"
    )


if TYPE_CHECKING:
    from boss.core.app_api import AppAPI


def run(stop_event: threading.Event, api: "AppAPI") -> None:
    cfg = api.get_app_config()
    refresh = float(cfg.get("refresh_seconds", 1800))
    timeout = float(cfg.get("request_timeout_seconds", 6))
    last_fetch = 0.0

    def _show() -> None:
        try:
            country = _fetch(timeout)
            body = _format(country)
            api.screen.clear()
            api.screen.display_text(f"Country Fact\n\n{body}", align="left", font_size=16)
        except Exception as exc:
            api.screen.clear()
            api.screen.display_text(f"Country Fact\n\nErr: {exc}", align="left")

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
