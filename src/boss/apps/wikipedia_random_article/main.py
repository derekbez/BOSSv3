"""Wikipedia Random Article — random summary with pagination.

Yellow/Blue = prev/next page, Green = new article.
"""

from __future__ import annotations

import threading
import time
from typing import TYPE_CHECKING, Any

from boss.apps._lib.http_helpers import fetch_json
from boss.apps._lib.paginator import TextPaginator, wrap_paragraphs

API_URL = "https://en.wikipedia.org/api/rest_v1/page/random/summary"


def _fetch(timeout: float) -> tuple[str, list[str], str | None]:
    data = fetch_json(API_URL, timeout=timeout)
    title = str(data.get("title", "Random Article"))
    extract = str(data.get("extract", "(no summary returned)")).strip()
    page_url = data.get("content_urls", {}).get("desktop", {}).get("page")
    lines = wrap_paragraphs([extract], width=92, sep_blank=False)
    return title, lines, page_url


if TYPE_CHECKING:
    from boss.core.app_api import AppAPI


def run(stop_event: threading.Event, api: "AppAPI") -> None:
    cfg = api.get_app_config()
    refresh = float(cfg.get("refresh_seconds", 900))
    timeout = float(cfg.get("request_timeout_seconds", 6))
    per_page = int(cfg.get("lines_per_page", 10))
    article_title = "Wikipedia"
    article_url: str | None = None
    last_fetch = 0.0

    def _led(color: str, on: bool) -> None:
        api.hardware.set_led(color, on)

    paginator = TextPaginator([], per_page, led_update=_led, prev_color="yellow", next_color="blue")

    def _render() -> None:
        page_lines = paginator.page_lines()
        body = "\n".join(page_lines) if page_lines else "(no data)"
        pg = f"({paginator.page + 1}/{paginator.total_pages})"
        footer = ""
        if article_url and paginator.page == paginator.total_pages - 1:
            footer = f"\n\nLink: {article_url}"
        api.screen.clear()
        api.screen.display_text(
            f"{article_title} {pg}\n\n{body}{footer}\n\n[YEL] Prev  [GRN] New  [BLU] Next",
            align="left",
            font_size=16,
        )

    def _refresh() -> None:
        nonlocal article_title, article_url
        try:
            article_title, lines, article_url = _fetch(timeout)
            paginator.set_lines(lines)
            paginator.reset()
        except Exception as exc:
            article_title = "Wikipedia"
            article_url = None
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
