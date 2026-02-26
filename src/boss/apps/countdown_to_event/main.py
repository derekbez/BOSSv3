"""Countdown to Event — configurable target date/time countdown.

Green = refresh.
"""

from __future__ import annotations

from datetime import date, datetime, time as dt_time
import threading
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from boss.core.app_api import AppAPI


def _parse_target(target_date: str, target_time: str) -> datetime:
    date_part = date.fromisoformat(target_date)
    try:
        time_part = dt_time.fromisoformat(target_time)
    except Exception:
        time_part = dt_time(hour=0, minute=0, second=0)
    return datetime.combine(date_part, time_part)


def _format_delta(seconds: int) -> str:
    seconds = max(0, int(seconds))
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, secs = divmod(rem, 60)
    return f"{days}d {hours}h {minutes}m {secs}s"


def run(stop_event: threading.Event, api: "AppAPI") -> None:
    cfg = api.get_app_config()
    event_name = str(cfg.get("event_name", "Event"))
    target_date = str(cfg.get("target_date", "2026-12-25"))
    target_time = str(cfg.get("target_time", "00:00:00"))
    refresh = float(cfg.get("refresh_seconds", 30))

    title = "Countdown"
    last_refresh = 0.0

    def _show() -> None:
        try:
            target = _parse_target(target_date, target_time)
            now = datetime.now()
            delta_sec = int((target - now).total_seconds())
            if delta_sec >= 0:
                status = "Time remaining"
                countdown = _format_delta(delta_sec)
            else:
                status = "Event passed"
                countdown = _format_delta(abs(delta_sec)) + " ago"

            api.screen.clear()
            api.screen.display_text(
                (
                    f"{title}\n\n"
                    f"{event_name}\n"
                    f"Target: {target_date} {target_time}\n\n"
                    f"{status}:\n"
                    f"{countdown}"
                ),
                align="left",
                font_size=20,
            )
        except Exception as exc:
            api.screen.clear()
            api.screen.display_text(f"{title}\n\nErr: {exc}", align="left")

    def on_button(event: Any) -> None:
        nonlocal last_refresh
        payload = event.payload or {}
        if payload.get("button") == "green":
            last_refresh = time.time()
            _show()

    api.hardware.set_led("green", True)
    sub_id = api.event_bus.subscribe("input.button.pressed", on_button)
    try:
        _show()
        last_refresh = time.time()
        while not stop_event.is_set():
            if time.time() - last_refresh >= refresh:
                last_refresh = time.time()
                _show()
            stop_event.wait(0.25)
    finally:
        api.event_bus.unsubscribe(sub_id)
        api.hardware.set_led("green", False)
