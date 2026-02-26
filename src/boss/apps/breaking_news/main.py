"""Breaking News — headlines from NewsData.io with pagination.

Yellow = prev page, Green = refresh, Blue = next page.
"""

from __future__ import annotations

import time
import threading
from typing import TYPE_CHECKING, Any

from boss.apps._lib.http_helpers import fetch_json
from boss.apps._lib.paginator import TextPaginator, wrap_plain

API_URL = "https://newsdata.io/api/1/news"


def _fetch(api_key: str, country: str, category: str, timeout: float) -> list[str]:
    if not api_key:
        raise RuntimeError("No NewsData API key set")
    data = fetch_json(
        API_URL,
        params={"apikey": api_key, "country": country, "category": category, "language": "en"},
        timeout=timeout,
    )
    articles = data.get("results", [])
    heads: list[str] = []
    for a in articles:
        title = a.get("title")
        if title:
            heads.append(title[:120])
        if len(heads) >= 8:
            break
    if not heads:
        raise ValueError("No headlines")
    return heads


if TYPE_CHECKING:
    from boss.core.app_api import AppAPI


def run(stop_event: threading.Event, api: "AppAPI") -> None:
    cfg = api.get_app_config()
    api_key = cfg.get("api_key") or api.get_secret("BOSS_APP_NEWSDATA_API_KEY")
    country = cfg.get("country", "gb")
    category = cfg.get("category", "technology")
    refresh = float(cfg.get("refresh_seconds", 300))
    timeout = float(cfg.get("request_timeout_seconds", 6))
    title = "Headlines"
    per_page = 8
    last_fetch = 0.0

    def _led(color: str, on: bool) -> None:
        api.hardware.set_led(color, on)

    paginator = TextPaginator([], per_page, led_update=_led)

    def _render() -> None:
        page_text = "\n".join(paginator.page_lines()) or "(no data)"
        pg = f"({paginator.page + 1}/{paginator.total_pages})"
        api.screen.clear()
        api.screen.display_text(
            f"{title} {pg}\n\n{page_text}\n\n[YEL] Prev  [GRN] Refresh  [BLU] Next",
            font_size=16, align="left",
        )

    def _refresh() -> None:
        try:
            heads = _fetch(api_key, country, category, timeout)
            lines: list[str] = []
            for h in heads:
                lines.extend(wrap_plain(h, width=100))
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
            stop_event.wait(0.25)
    finally:
        api.event_bus.unsubscribe(sub_id)
        api.hardware.set_led("green", False)
        api.hardware.set_led("yellow", False)
        api.hardware.set_led("blue", False)
