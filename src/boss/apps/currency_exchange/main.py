"""Currency Exchange — live FX rates with pair cycling.

Yellow/Blue = previous/next pair, Green = refresh.
"""

from __future__ import annotations

from datetime import date, timedelta
import threading
import time
from typing import TYPE_CHECKING, Any

from boss.apps._lib.http_helpers import fetch_json

API_URL = "https://api.frankfurter.app"


def _fetch_pair(base: str, target: str, timeout: float) -> tuple[float, float | None]:
    latest = fetch_json(
        f"{API_URL}/latest",
        params={"from": base, "to": target},
        timeout=timeout,
    )
    latest_rate = float(latest.get("rates", {}).get(target, 0.0))

    prev_rate: float | None = None
    prev_day = (date.today() - timedelta(days=1)).isoformat()
    try:
        prev = fetch_json(
            f"{API_URL}/{prev_day}",
            params={"from": base, "to": target},
            timeout=timeout,
        )
        prev_rate = float(prev.get("rates", {}).get(target, 0.0))
    except Exception:
        prev_rate = None

    return latest_rate, prev_rate


def _trend_symbol(latest_rate: float, prev_rate: float | None) -> str:
    if prev_rate is None or prev_rate <= 0:
        return "~"
    if latest_rate > prev_rate:
        return "▲"
    if latest_rate < prev_rate:
        return "▼"
    return "="


if TYPE_CHECKING:
    from boss.core.app_api import AppAPI


def run(stop_event: threading.Event, api: "AppAPI") -> None:
    cfg = api.get_app_config()
    base = str(cfg.get("base_currency", "GBP")).upper()
    pairs = [str(x).upper() for x in cfg.get("target_currencies", ["USD", "EUR", "JPY", "AUD", "CHF"]) if str(x).strip()]
    if not pairs:
        pairs = ["USD"]
    refresh = float(cfg.get("refresh_seconds", 300))
    timeout = float(cfg.get("request_timeout_seconds", 6))
    title = "Currency Exchange"
    last_fetch = 0.0
    idx = 0

    def _show() -> None:
        target = pairs[idx]
        try:
            latest_rate, prev_rate = _fetch_pair(base, target, timeout)
            trend = _trend_symbol(latest_rate, prev_rate)
            prev_text = f"{prev_rate:.4f}" if prev_rate is not None and prev_rate > 0 else "n/a"
            api.screen.clear()
            api.screen.display_text(
                (
                    f"{title}\n\n"
                    f"Pair: {base} → {target}  ({idx + 1}/{len(pairs)})\n"
                    f"Rate: {latest_rate:.4f}  {trend}\n"
                    f"Prev: {prev_text}\n\n"
                    f"[YEL] Prev  [GRN] Refresh  [BLU] Next"
                ),
                align="left",
                font_size=18,
            )
        except Exception as exc:
            api.screen.clear()
            api.screen.display_text(f"{title}\n\nErr: {exc}", align="left")

    def on_button(event: Any) -> None:
        nonlocal idx, last_fetch
        btn = event.payload.get("button")
        if btn == "green":
            last_fetch = time.time()
            _show()
        elif btn == "yellow":
            idx = (idx - 1) % len(pairs)
            _show()
        elif btn == "blue":
            idx = (idx + 1) % len(pairs)
            _show()

    api.hardware.set_led("yellow", True)
    api.hardware.set_led("green", True)
    api.hardware.set_led("blue", True)
    sub_id = api.event_bus.subscribe("input.button.pressed", on_button)
    try:
        _show()
        last_fetch = time.time()
        while not stop_event.is_set():
            if time.time() - last_fetch >= refresh:
                last_fetch = time.time()
                _show()
            stop_event.wait(0.25)
    finally:
        api.event_bus.unsubscribe(sub_id)
        api.hardware.set_led("yellow", False)
        api.hardware.set_led("green", False)
        api.hardware.set_led("blue", False)
