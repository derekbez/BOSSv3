"""Tiny Poem — random poem from Poemist API with pagination.

Yellow = prev page, Green = new poem, Blue = next page.
"""

from __future__ import annotations

import time
import threading
from typing import TYPE_CHECKING, Any

from boss.apps._lib.http_helpers import fetch_json
from boss.apps._lib.paginator import TextPaginator, wrap_paragraphs

API_URL = "https://www.poemist.com/api/v1/randompoems"


def _fetch(timeout: float) -> tuple[str, list[str]]:
    """Return (header, wrapped_lines) for a random poem."""
    data = fetch_json(API_URL, timeout=timeout)
    if not data or not isinstance(data, list):
        return "Tiny Poem", ["(no poem returned)"]
    poem = data[0]
    title = poem.get("title", "Untitled")
    content = poem.get("content", "").strip()
    author = poem.get("poet", {}).get("name", "Unknown")
    header = f"{title}  — {author}"
    paragraphs = content.split("\n") if content else ["(empty)"]
    lines = wrap_paragraphs(paragraphs, width=80, sep_blank=True)
    return header, lines


if TYPE_CHECKING:
    from boss.core.app_api import AppAPI


def run(stop_event: threading.Event, api: "AppAPI") -> None:
    cfg = api.get_app_config()
    refresh = float(cfg.get("refresh_seconds", 10800))
    timeout = float(cfg.get("request_timeout_seconds", 6))
    per_page = int(cfg.get("lines_per_page", 12))
    last_fetch = 0.0
    poem_header = "Tiny Poem"

    def _led(color: str, on: bool) -> None:
        api.hardware.set_led(color, on)

    paginator = TextPaginator([], per_page, led_update=_led)

    def _render() -> None:
        page_lines = paginator.page_lines()
        body = "\n".join(page_lines) if page_lines else "(no data)"
        pg = f"({paginator.page + 1}/{paginator.total_pages})"
        api.screen.clear()
        api.screen.display_text(
            f"{poem_header} {pg}\n\n{body}",
            font_size=16,
            align="left",
        )

    def _refresh() -> None:
        nonlocal poem_header
        try:
            poem_header, lines = _fetch(timeout)
            paginator.set_lines(lines)
            paginator.reset()
        except Exception as exc:
            poem_header = "Tiny Poem"
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
