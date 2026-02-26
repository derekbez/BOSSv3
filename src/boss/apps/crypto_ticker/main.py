"""Crypto Ticker — live coin prices with coin cycling.

Yellow/Blue = previous/next coin, Green = refresh.
"""

from __future__ import annotations

import threading
import time
from typing import TYPE_CHECKING, Any

from boss.apps._lib.http_helpers import fetch_json

API_URL = "https://api.coingecko.com/api/v3/simple/price"


def _fetch(coins: list[str], currency: str, timeout: float) -> dict[str, dict[str, float]]:
    data = fetch_json(
        API_URL,
        params={
            "ids": ",".join(coins),
            "vs_currencies": currency,
            "include_24hr_change": "true",
        },
        timeout=timeout,
    )
    if not isinstance(data, dict) or not data:
        raise RuntimeError("No coin data")
    return data


def _trend_symbol(change_pct: float | None) -> str:
    if change_pct is None:
        return "~"
    if change_pct > 0:
        return "▲"
    if change_pct < 0:
        return "▼"
    return "="


if TYPE_CHECKING:
    from boss.core.app_api import AppAPI


def run(stop_event: threading.Event, api: "AppAPI") -> None:
    cfg = api.get_app_config()
    coins = [str(c).strip().lower() for c in cfg.get("coins", ["bitcoin", "ethereum", "solana"]) if str(c).strip()]
    if not coins:
        coins = ["bitcoin"]
    currency = str(cfg.get("vs_currency", "gbp")).strip().lower() or "gbp"
    refresh = float(cfg.get("refresh_seconds", 180))
    timeout = float(cfg.get("request_timeout_seconds", 6))

    idx = 0
    last_fetch = 0.0
    cache: dict[str, dict[str, float]] = {}

    def _render() -> None:
        coin = coins[idx]
        entry = cache.get(coin, {})
        price = entry.get(currency)
        change = entry.get(f"{currency}_24h_change")
        price_text = f"{price:,.2f}" if isinstance(price, (int, float)) else "n/a"
        change_text = f"{change:+.2f}%" if isinstance(change, (int, float)) else "n/a"
        trend = _trend_symbol(change if isinstance(change, (int, float)) else None)
        api.screen.clear()
        api.screen.display_text(
            (
                f"Crypto Ticker\n\n"
                f"Coin: {coin} ({idx + 1}/{len(coins)})\n"
                f"Price: {price_text} {currency.upper()}\n"
                f"24h: {change_text} {trend}\n\n"
                "[YEL] Prev  [GRN] Refresh  [BLU] Next"
            ),
            align="left",
            font_size=18,
        )

    def _refresh() -> None:
        nonlocal cache
        try:
            cache = _fetch(coins, currency, timeout)
        except Exception as exc:
            api.screen.clear()
            api.screen.display_text(f"Crypto Ticker\n\nErr: {exc}", align="left")
            return
        _render()

    def on_button(event: Any) -> None:
        nonlocal idx, last_fetch
        payload = event.payload or {}
        btn = payload.get("button")
        if btn == "green":
            last_fetch = time.time()
            _refresh()
        elif btn == "yellow":
            idx = (idx - 1) % len(coins)
            _render()
        elif btn == "blue":
            idx = (idx + 1) % len(coins)
            _render()

    api.hardware.set_led("yellow", True)
    api.hardware.set_led("green", True)
    api.hardware.set_led("blue", True)
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
        api.hardware.set_led("yellow", False)
        api.hardware.set_led("green", False)
        api.hardware.set_led("blue", False)
