"""Constellation of the Night — static placeholder message."""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from boss.core.app_api import AppAPI


def run(stop_event: threading.Event, api: "AppAPI") -> None:
    cfg = api.get_app_config()
    message = cfg.get("message", "Orion visible tonight! (placeholder)")
    api.screen.clear()
    api.screen.display_text(f"Constellation\n\n{message}", align="left")
    while not stop_event.is_set():
        stop_event.wait(0.5)
