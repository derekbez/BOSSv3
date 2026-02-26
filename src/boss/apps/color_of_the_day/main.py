"""Color of the Day — random colour from ColourLovers (XML) with date-hash fallback.

Uses ``display_html()`` to render a colour swatch.  Green = refresh.
"""

from __future__ import annotations

import hashlib
import time
import xml.etree.ElementTree as ET
import threading
from datetime import date
from typing import TYPE_CHECKING, Any

from boss.apps._lib.http_helpers import fetch_text

API_URL = "https://www.colourlovers.com/api/colors/random?format=xml"


def _fetch_api(timeout: float) -> tuple[str, str]:
    """Try ColourLovers API; returns (name, hex)."""
    body = fetch_text(API_URL, timeout=timeout)
    root = ET.fromstring(body)
    color = root.find("color")
    if color is None:
        raise ValueError("No <color> element")
    title = (color.findtext("title") or "?").strip()
    hexcode = (color.findtext("hex") or "??????").strip()
    return title, hexcode


def _fallback_color() -> tuple[str, str]:
    """Deterministic colour derived from today's date."""
    today = date.today().isoformat()
    hexcode = hashlib.md5(today.encode()).hexdigest()[:6]  # noqa: S324
    return "Daily Blend", hexcode


def _swatch_html(name: str, hexcode: str) -> str:
    """Build an HTML snippet showing a colour swatch + label."""
    return (
        f'<div style="text-align:center;padding:1em">'
        f'<div style="width:120px;height:120px;margin:0 auto 0.5em;'
        f"background:#{hexcode};border:2px solid #555;border-radius:12px\"></div>"
        f"<div style=\"font-size:28px;font-weight:bold\">#{hexcode}</div>"
        f"<div style=\"font-size:22px;color:#777;margin-top:0.2em\">{name}</div>"
        f"</div>"
    )


if TYPE_CHECKING:
    from boss.core.app_api import AppAPI


def run(stop_event: threading.Event, api: "AppAPI") -> None:
    cfg = api.get_app_config()
    refresh = float(cfg.get("refresh_seconds", 86400))
    timeout = float(cfg.get("request_timeout_seconds", 6))
    last_fetch = 0.0

    def _show() -> None:
        try:
            cname, hexcode = _fetch_api(timeout)
        except Exception:
            cname, hexcode = _fallback_color()
        api.screen.clear()
        api.screen.display_html(_swatch_html(cname, hexcode))

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
