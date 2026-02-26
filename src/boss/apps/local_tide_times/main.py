"""Local Tide Times — WorldTides API.  Green = refresh."""

from __future__ import annotations

import time
from datetime import datetime, timezone
import threading
from typing import TYPE_CHECKING, Any

from boss.apps._lib.http_helpers import fetch_json

API_URL = "https://www.worldtides.info/api/v3"


def _fetch(lat: float, lon: float, api_key: str, timeout: float) -> str:
    if not api_key:
        return "(no WorldTides API key set)"
    data = fetch_json(
        API_URL,
        params={"extremes": "", "lat": str(lat), "lon": str(lon), "key": api_key},
        timeout=timeout,
    )
    extremes = data.get("extremes", [])
    if not extremes:
        return "(no tide data)"
    lines: list[str] = []
    for ex in extremes[:6]:
        dt_val = ex.get("date") or ex.get("dt", 0)
        if isinstance(dt_val, (int, float)):
            ts = datetime.fromtimestamp(dt_val, tz=timezone.utc).strftime("%H:%M")
        else:
            ts = str(dt_val)[:16]
        tide_type = ex.get("type", "?")
        height = ex.get("height", 0)
        lines.append(f"{ts}  {tide_type:4s}  {height:+.1f}m")
    return "\n".join(lines)


if TYPE_CHECKING:
    from boss.core.app_api import AppAPI


def run(stop_event: threading.Event, api: "AppAPI") -> None:
    cfg = api.get_app_config()
    refresh = float(cfg.get("refresh_seconds", 10800))
    timeout = float(cfg.get("request_timeout_seconds", 6))
    api_key = cfg.get("api_key") or api.get_secret("BOSS_APP_WORLDTIDES_API_KEY")
    loc = api.get_global_location()
    lat, lon = loc["lat"], loc["lon"]
    title = "Tides"
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
