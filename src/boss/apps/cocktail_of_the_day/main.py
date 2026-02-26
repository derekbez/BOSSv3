"""Cocktail of the Day — random cocktail recipe with pagination.

Yellow/Blue = prev/next page, Green = new cocktail.
"""

from __future__ import annotations

import threading
import time
from typing import TYPE_CHECKING, Any

from boss.apps._lib.http_helpers import fetch_json
from boss.apps._lib.paginator import TextPaginator, wrap_paragraphs

API_URL = "https://www.thecocktaildb.com/api/json/v1/1/random.php"


def _fetch(timeout: float) -> tuple[str, list[str]]:
    data = fetch_json(API_URL, timeout=timeout)
    drinks = data.get("drinks", [])
    if not drinks:
        raise RuntimeError("No cocktail returned")
    drink = drinks[0]

    name = str(drink.get("strDrink", "Cocktail"))
    category = str(drink.get("strCategory", ""))
    glass = str(drink.get("strGlass", ""))
    instructions = str(drink.get("strInstructions", "")).strip()

    parts: list[str] = []
    if category:
        parts.append(f"Category: {category}")
    if glass:
        parts.append(f"Glass: {glass}")

    ingredients: list[str] = []
    for i in range(1, 16):
        ing = str(drink.get(f"strIngredient{i}", "")).strip()
        meas = str(drink.get(f"strMeasure{i}", "")).strip()
        if ing:
            ingredients.append(f"- {meas} {ing}".strip())

    if ingredients:
        parts.append("Ingredients:")
        parts.extend(ingredients)

    if instructions:
        parts.append("")
        parts.append("Instructions:")
        parts.append(instructions)

    lines = wrap_paragraphs(parts, width=92, sep_blank=False)
    return name, lines


if TYPE_CHECKING:
    from boss.core.app_api import AppAPI


def run(stop_event: threading.Event, api: "AppAPI") -> None:
    cfg = api.get_app_config()
    refresh = float(cfg.get("refresh_seconds", 3600))
    timeout = float(cfg.get("request_timeout_seconds", 6))
    per_page = int(cfg.get("lines_per_page", 10))

    title = "Cocktail of the Day"
    last_fetch = 0.0

    def _led(color: str, on: bool) -> None:
        api.hardware.set_led(color, on)

    paginator = TextPaginator([], per_page, led_update=_led, prev_color="yellow", next_color="blue")

    def _render() -> None:
        page_lines = paginator.page_lines()
        body = "\n".join(page_lines) if page_lines else "(no data)"
        pg = f"({paginator.page + 1}/{paginator.total_pages})"
        api.screen.clear()
        api.screen.display_text(
            f"{title} {pg}\n\n{body}\n\n[YEL] Prev  [GRN] New  [BLU] Next",
            align="left",
            font_size=16,
        )

    def _refresh() -> None:
        nonlocal title
        try:
            name, lines = _fetch(timeout)
            title = name
            paginator.set_lines(lines)
            paginator.reset()
        except Exception as exc:
            title = "Cocktail of the Day"
            paginator.set_lines([f"Err: {exc}"])
            paginator.reset()
        _render()

    def on_button(event: Any) -> None:
        nonlocal last_fetch
        payload = event.payload or {}
        btn = payload.get("button")
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
