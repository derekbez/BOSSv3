"""Bird Sightings Near Me — eBird API with pagination.

Yellow = prev, Green = refresh, Blue = next.  Requires global location.
"""

from __future__ import annotations

import time
import threading
from typing import TYPE_CHECKING, Any

from boss.apps._lib.http_helpers import fetch_json
from boss.apps._lib.paginator import TextPaginator, wrap_plain

API_TMPL = "https://api.ebird.org/v2/data/obs/geo/recent?lat={lat}&lng={lng}&dist={radius}&back=7"


def _fetch(lat: float, lon: float, radius: int, api_key: str, timeout: float) -> list[tuple[str, str]]:
    if not api_key:
        raise RuntimeError("No eBird API key set")
    url = API_TMPL.format(lat=lat, lng=lon, radius=radius)
    data = fetch_json(url, headers={"X-eBirdApiToken": api_key.strip()}, timeout=timeout)
    sightings: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for entry in data:
        name = entry.get("comName") or entry.get("sciName") or ""
        loc = entry.get("locName") or ""
        if name and (name, loc) not in seen:
            sightings.append((name, loc))
            seen.add((name, loc))
    if not sightings:
        return [("No recent sightings in this area.", "")]
    return sightings


if TYPE_CHECKING:
    from boss.core.app_api import AppAPI


def run(stop_event: threading.Event, api: "AppAPI") -> None:
    cfg = api.get_app_config()
    loc = api.get_global_location()
    lat, lon = loc["lat"], loc["lon"]
    radius = int(cfg.get("radius", 10))
    per_page = int(cfg.get("per_page", 10))
    refresh = float(cfg.get("refresh_seconds", 120))
    timeout = float(cfg.get("request_timeout_seconds", 6))
    api_key = api.get_secret("BOSS_APP_EBIRD_API_KEY")
    title = "Nearby Birds"
    last_fetch = 0.0
    cache: list[tuple[str, str]] = []

    def _led(color: str, on: bool) -> None:
        api.hardware.set_led(color, on)

    paginator = TextPaginator([], per_page, led_update=_led, prev_color="yellow", next_color="blue")

    def _rebuild() -> list[str]:
        lines: list[str] = []
        for name, loc_name in cache:
            base = f"{name} @ {loc_name}" if loc_name else name
            lines.extend(wrap_plain(base, width=100))
        return lines

    def _render() -> None:
        page_lines = paginator.page_lines()
        body = "\n".join(page_lines) if page_lines else "(no data)"
        pg = f"({paginator.page + 1}/{paginator.total_pages})"
        total = len(cache)
        api.screen.clear()
        api.screen.display_text(
            f"{title} {pg}  r={radius}  n={total}\n\n{body}\n\n[YEL] Prev  [GRN] Refresh  [BLU] Next",
            font_size=16, align="left",
        )

    def _refresh() -> None:
        nonlocal cache
        try:
            cache = _fetch(lat, lon, radius, api_key, timeout)
            paginator.set_lines(_rebuild())
            paginator.reset()
        except Exception as exc:
            cache = []
            paginator.set_lines([f"Err: {exc}"])
            paginator.reset()
        _render()

    def on_button(event: Any) -> None:
        nonlocal last_fetch
        btn = event.payload.get("button")
        if btn == "green":
            last_fetch = time.time()
            _refresh()
        elif btn == "yellow":
            if paginator.prev():
                _render()
        elif btn == "blue":
            if paginator.next():
                _render()

    api.hardware.set_led("green", True)
    sub_id = api.event_bus.subscribe("input.button.pressed", on_button)
    try:
        _refresh()
        last_fetch = time.time()
        while not stop_event.is_set():
            if time.time() - last_fetch >= refresh:
                last_fetch = time.time()
                _refresh()
            stop_event.wait(0.25)
    finally:
        api.event_bus.unsubscribe(sub_id)
        api.hardware.set_led("green", False)
        api.hardware.set_led("yellow", False)
        api.hardware.set_led("blue", False)
