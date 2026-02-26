"""On This Day — historical events from byabbe.se with pagination.

Yellow = prev, Green = refresh, Blue = next.
"""

from __future__ import annotations

import time
from datetime import date
import threading
from typing import TYPE_CHECKING, Any

from boss.apps._lib.http_helpers import fetch_json
from boss.apps._lib.paginator import TextPaginator, wrap_events

API_URL = "https://byabbe.se/on-this-day/{month}/{day}/events.json"


def _fetch(timeout: float) -> list[tuple[str, str]]:
    today = date.today()
    url = API_URL.format(month=today.month, day=today.day)
    data = fetch_json(url, timeout=timeout)
    raw_events = data.get("events", [])
    if not raw_events:
        raise ValueError("No events")
    events: list[tuple[str, str]] = []
    for ev in raw_events:
        year = ev.get("year", "?")
        desc = ev.get("description", "")
        if desc:
            events.append((str(year), desc))
    return events


if TYPE_CHECKING:
    from boss.core.app_api import AppAPI


def run(stop_event: threading.Event, api: "AppAPI") -> None:
    cfg = api.get_app_config()
    refresh = float(cfg.get("refresh_seconds", 43200))
    timeout = float(cfg.get("request_timeout_seconds", 6))
    wrap_width = int(cfg.get("wrap_width", 100))
    per_page = 10
    title = "On This Day"
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
            f"{title} {pg}\n\n{body}\n\n[YEL] Prev  [GRN] Refresh  [BLU] Next",
            font_size=16, align="left",
        )

    def _refresh() -> None:
        try:
            events = _fetch(timeout)
            lines = wrap_events(events, wrap_width)
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
            stop_event.wait(0.5)
    finally:
        api.event_bus.unsubscribe(sub_id)
        api.hardware.set_led("green", False)
        api.hardware.set_led("yellow", False)
        api.hardware.set_led("blue", False)
