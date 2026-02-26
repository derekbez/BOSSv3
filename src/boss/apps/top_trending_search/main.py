"""Top Trending Search — Google Trends via SerpApi (public API rewrite).

The v2 version hit a local backend at localhost:3000.  v3 uses SerpApi's
Google Trends endpoint directly so no backend is needed.  Green = refresh.
"""

from __future__ import annotations

import time
import threading
from typing import TYPE_CHECKING, Any

from boss.apps._lib.http_helpers import fetch_json

API_URL = "https://serpapi.com/search.json"


def _fetch(api_key: str, geo: str, timeout: float) -> str:
    if not api_key:
        return "(no SerpApi API key — set BOSS_APP_SERPAPI_API_KEY)"
    data = fetch_json(
        API_URL,
        params={
            "engine": "google_trends_trending_now",
            "geo": geo,
            "api_key": api_key,
        },
        timeout=timeout,
    )
    trends = data.get("trending_searches", [])
    if not trends:
        return "(no trends found)"
    lines: list[str] = []
    for t in trends[:8]:
        query = t.get("query", "?")
        lines.append(query)
    return "\n".join(lines)


if TYPE_CHECKING:
    from boss.core.app_api import AppAPI


def run(stop_event: threading.Event, api: "AppAPI") -> None:
    cfg = api.get_app_config()
    refresh = float(cfg.get("refresh_seconds", 3600))
    timeout = float(cfg.get("request_timeout_seconds", 6))
    geo = cfg.get("geo", "GB")
    api_key = cfg.get("api_key") or api.get_secret("BOSS_APP_SERPAPI_API_KEY")
    title = "Trending"
    last_fetch = 0.0

    def _show() -> None:
        try:
            text = _fetch(api_key, geo, timeout)
            api.screen.clear()
            api.screen.display_text(f"{title}\n\n{text}", align="left")
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
