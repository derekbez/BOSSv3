"""Hello World — comprehensive BOSS API demonstration.

Cycles LEDs, counts button presses per colour, and shows a live
dashboard on screen.  Press RED to exit.
"""

from __future__ import annotations

import time
import threading
from typing import TYPE_CHECKING, Any

LED_COLORS = ["red", "yellow", "green", "blue"]


if TYPE_CHECKING:
    from boss.core.app_api import AppAPI


def run(stop_event: threading.Event, api: "AppAPI") -> None:
    api.log_info("hello_world starting")
    counts: dict[str, int] = {c: 0 for c in LED_COLORS}
    sub_ids: list[str] = []

    # -- helpers ----------------------------------------------------------

    def _set_all_leds(on: bool) -> None:
        for c in LED_COLORS:
            try:
                api.hardware.set_led(c, on)
            except Exception:
                pass

    def _blink(times: int = 2, on_sec: float = 0.20, off_sec: float = 0.15) -> None:
        for _ in range(times):
            if stop_event.is_set():
                return
            _set_all_leds(True)
            if stop_event.wait(on_sec):
                return
            _set_all_leds(False)
            if stop_event.wait(off_sec):
                return

    def _render() -> None:
        lines = [
            "Hello BOSS!",
            "",
            "Button presses:",
        ]
        for c in LED_COLORS:
            lines.append(f"  [{c.upper():6s}] {counts[c]}")
        lines.append("")
        lines.append("[RED] to exit")
        api.screen.clear()
        api.screen.display_text("\n".join(lines), font_size=18, align="left")

    # -- button handler ---------------------------------------------------

    def on_button(event: Any) -> None:
        button = event.payload.get("button")
        if button not in LED_COLORS:
            return
        counts[button] += 1
        # brief LED off-on feedback
        try:
            api.hardware.set_led(button, False)
            time.sleep(0.05)
            api.hardware.set_led(button, True)
        except Exception:
            pass
        if button == "red":
            stop_event.set()
            return
        _render()

    # -- main body --------------------------------------------------------

    api.screen.clear()
    api.screen.display_text("Starting BOSS demo…", font_size=24, align="center")
    _blink(times=2)

    for c in LED_COLORS:
        api.hardware.set_led(c, True)
    _render()

    sub_ids.append(api.event_bus.subscribe("input.button.pressed", on_button))

    last_activity = time.monotonic()
    try:
        while not stop_event.is_set():
            if time.monotonic() - last_activity > 30:
                _blink(times=1)
                last_activity = time.monotonic()
                for c in LED_COLORS:
                    api.hardware.set_led(c, True)
            stop_event.wait(0.5)
    finally:
        for sid in sub_ids:
            api.event_bus.unsubscribe(sid)
        _set_all_leds(False)
        api.log_info("hello_world stopping")
