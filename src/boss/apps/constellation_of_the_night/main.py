"""Constellation of the Night — static placeholder message."""

from __future__ import annotations

from threading import Event
from typing import Any


def run(stop_event: Event, api: Any) -> None:
    cfg = api.get_app_config()
    message = cfg.get("message", "Orion visible tonight! (placeholder)")
    api.screen.clear()
    api.screen.display_text(f"Constellation\n\n{message}", align="left")
    while not stop_event.is_set():
        stop_event.wait(0.5)
