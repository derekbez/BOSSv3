"""Color of the Day — random colour from ColourLovers (XML).  Green = refresh."""

from __future__ import annotations

import time
import xml.etree.ElementTree as ET
import threading
from typing import TYPE_CHECKING, Any

from boss.apps._lib.http_helpers import fetch_text

API_URL = "https://www.colourlovers.com/api/colors/random?format=xml"


def _fetch(timeout: float) -> tuple[str, str]:
    body = fetch_text(API_URL, timeout=timeout)
    root = ET.fromstring(body)
    color = root.find("color")
    if color is None:
        raise ValueError("No <color> element")
    title = (color.findtext("title") or "?").strip()
    hexcode = (color.findtext("hex") or "??????").strip()
    return title, hexcode


if TYPE_CHECKING:
    from boss.core.app_api import AppAPI


def run(stop_event: threading.Event, api: "AppAPI") -> None:
    cfg = api.get_app_config()
    refresh = float(cfg.get("refresh_seconds", 86400))
    timeout = float(cfg.get("request_timeout_seconds", 6))
    title = "Color of Day"
    last_fetch = 0.0

    def _show() -> None:
        try:
            cname, hexcode = _fetch(timeout)
            api.screen.clear()
            api.screen.display_text(f"{title}\n\n{cname}\n#{hexcode}", align="center")
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
