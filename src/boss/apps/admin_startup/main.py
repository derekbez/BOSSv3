"""Admin Startup — LED blink animation + 'BOSS Ready' on boot."""

from __future__ import annotations

from threading import Event
from typing import Any

LED_COLORS = ["red", "yellow", "green", "blue"]


def run(stop_event: Event, api: Any) -> None:
    api.log_info("admin_startup: initializing")

    def _set_all(on: bool) -> None:
        for c in LED_COLORS:
            try:
                api.hardware.set_led(c, on)
            except Exception:
                pass

    def _blink(times: int = 2, on_sec: float = 0.22, off_sec: float = 0.16) -> None:
        for _ in range(times):
            if stop_event.is_set():
                return
            _set_all(True)
            if stop_event.wait(on_sec):
                return
            _set_all(False)
            if stop_event.wait(off_sec):
                return

    try:
        api.screen.clear()
        api.screen.display_text("Starting BOSS…", font_size=32, align="center")
    except Exception as exc:
        api.log_error(f"admin_startup: screen init error: {exc}")

    try:
        _blink(times=2)
        api.screen.display_text("BOSS Ready", align="left", color="green", font_size=48)
        api.log_info("admin_startup: displayed 'BOSS Ready'")
        stop_event.wait(0.4)
    finally:
        _set_all(False)
