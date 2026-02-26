"""Admin Shutdown — reboot / poweroff / exit-to-OS menu.

Yellow = Reboot, Blue = Poweroff, Green = Exit to OS.
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from boss.core.app_api import AppAPI


def run(stop_event: threading.Event, api: "AppAPI") -> None:
    prompt = (
        "Shutdown Menu:\n\n"
        "  [YELLOW] Reboot\n"
        "  [BLUE]   Poweroff\n"
        "  [GREEN]  Exit to OS\n"
    )
    api.hardware.set_led("yellow", True)
    api.hardware.set_led("blue", True)
    api.hardware.set_led("green", True)
    api.hardware.set_led("red", False)
    api.screen.clear()
    api.screen.display_text(prompt, font_size=16, align="left")

    def on_button(event: Any) -> None:
        button = event.payload.get("button")
        if button == "yellow":
            api.screen.clear()
            api.screen.display_text("Rebooting system…", font_size=16, align="center")
            api.log_info("admin_shutdown: reboot triggered")
            api.event_bus.publish_threadsafe(
                "system.shutdown.requested",
                {"action": "reboot", "reason": "reboot"},
            )
            stop_event.set()
        elif button == "blue":
            api.screen.clear()
            api.screen.display_text("Shutting down system…", font_size=16, align="center")
            api.log_info("admin_shutdown: poweroff triggered")
            api.event_bus.publish_threadsafe(
                "system.shutdown.requested",
                {"action": "shutdown", "reason": "poweroff"},
            )
            stop_event.set()
        elif button == "green":
            api.screen.clear()
            api.screen.display_text("Exiting to OS shell…", font_size=16, align="center")
            api.log_info("admin_shutdown: exit-to-os triggered")
            api.event_bus.publish_threadsafe(
                "system.shutdown.requested",
                {"action": "exit", "reason": "exit_to_os"},
            )
            stop_event.set()

    sub_id = api.event_bus.subscribe("input.button.pressed", on_button)
    try:
        while not stop_event.is_set():
            stop_event.wait(0.2)
    finally:
        api.event_bus.unsubscribe(sub_id)
        for c in ("yellow", "blue", "green", "red"):
            api.hardware.set_led(c, False)
        api.screen.clear()
