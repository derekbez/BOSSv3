"""Earthquake Monitor — recent significant quakes with pagination.

Yellow/Blue = prev/next page, Green = refresh.
"""

from __future__ import annotations

from datetime import datetime, timezone
import threading
import time
from typing import TYPE_CHECKING, Any

from boss.apps._lib.http_helpers import fetch_json
from boss.apps._lib.paginator import TextPaginator, wrap_plain

API_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"


def _time_ago(when_ms: int) -> str:
    try:
        then = datetime.fromtimestamp(when_ms / 1000, tz=timezone.utc)
        delta = datetime.now(timezone.utc) - then
        mins = int(delta.total_seconds() // 60)
        if mins < 60:
            return f"{mins}m ago"
        hours = mins // 60
        if hours < 48:
            return f"{hours}h ago"
        return f"{hours // 24}d ago"
    except Exception:
        return "?"


def _fetch(limit: int, min_mag: float, timeout: float) -> list[str]:
    data = fetch_json(
        API_URL,
        params={
            "format": "geojson",
            "orderby": "time",
            "limit": str(limit),
            "minmagnitude": str(min_mag),
        },
        timeout=timeout,
    )
    features = data.get("features", [])
    if not features:
        return ["No recent earthquakes found."]

    lines: list[str] = []
    for f in features:
        props = f.get("properties", {})
        mag = props.get("mag")
        place = props.get("place", "Unknown place")
        when_ms = int(props.get("time", 0))
        age = _time_ago(when_ms)
        line = f"M{mag} {place} ({age})"
        lines.extend(wrap_plain(line, width=100))
    return lines


if TYPE_CHECKING:
    from boss.core.app_api import AppAPI


def run(stop_event: threading.Event, api: "AppAPI") -> None:
    cfg = api.get_app_config()
    refresh = float(cfg.get("refresh_seconds", 300))
    timeout = float(cfg.get("request_timeout_seconds", 6))
    min_mag = float(cfg.get("min_magnitude", 4.0))
    limit = int(cfg.get("limit", 12))
    per_page = int(cfg.get("lines_per_page", 8))
    last_fetch = 0.0

    def _led(color: str, on: bool) -> None:
        api.hardware.set_led(color, on)

    paginator = TextPaginator([], per_page, led_update=_led, prev_color="yellow", next_color="blue")

    def _render() -> None:
        page_lines = paginator.page_lines()
        body = "\n".join(page_lines) if page_lines else "(no data)"
        pg = f"({paginator.page + 1}/{paginator.total_pages})"
        api.screen.clear()
        api.screen.display_text(
            (
                f"Earthquake Monitor {pg}\n"
                f"min M{min_mag}\n\n"
                f"{body}\n\n"
                "[YEL] Prev  [GRN] Refresh  [BLU] Next"
            ),
            align="left",
            font_size=16,
        )

    def _refresh() -> None:
        try:
            lines = _fetch(limit=limit, min_mag=min_mag, timeout=timeout)
            paginator.set_lines(lines)
            paginator.reset()
        except Exception as exc:
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
