"""Number Guess — narrow range and guess target number.

Yellow = lower, Green = guess midpoint, Blue = higher.
"""

from __future__ import annotations

import random
import threading
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from boss.core.app_api import AppAPI


def run(stop_event: threading.Event, api: "AppAPI") -> None:
    cfg = api.get_app_config()
    low = int(cfg.get("min_number", 1))
    high = int(cfg.get("max_number", 100))
    if low >= high:
        low, high = 1, 100

    target = random.randint(low, high)
    lo = low
    hi = high
    attempts = 0
    message = "Use hints, then press GREEN to guess midpoint"

    def midpoint() -> int:
        return (lo + hi) // 2

    def _render() -> None:
        optimal = 0
        span = max(1, hi - lo + 1)
        while (1 << optimal) < span:
            optimal += 1
        api.screen.clear()
        api.screen.display_text(
            (
                "Number Guess\n\n"
                f"Range: [{lo}..{hi}]\n"
                f"Midpoint guess: {midpoint()}\n"
                f"Attempts: {attempts}\n"
                f"Optimal ≤ {optimal}\n\n"
                f"{message}\n\n"
                "[YEL] Lower  [GRN] Guess  [BLU] Higher"
            ),
            align="left",
            font_size=18,
        )

    def _new_game() -> None:
        nonlocal target, lo, hi, attempts, message
        target = random.randint(low, high)
        lo = low
        hi = high
        attempts = 0
        message = "New game started"
        _render()

    def on_button(event: Any) -> None:
        nonlocal lo, hi, attempts, message
        payload = event.payload or {}
        btn = payload.get("button")
        guess = midpoint()

        if btn == "yellow":
            hi = max(lo, guess - 1)
            message = f"Hint set: target < {guess}"
            _render()
        elif btn == "blue":
            lo = min(hi, guess + 1)
            message = f"Hint set: target > {guess}"
            _render()
        elif btn == "green":
            attempts += 1
            if guess == target:
                message = f"✅ Correct! It was {target}. Starting new game..."
                _render()
                stop_event.wait(1.2)
                if not stop_event.is_set():
                    _new_game()
            elif guess < target:
                lo = min(hi, guess + 1)
                message = f"Too low. New range starts above {guess}"
                _render()
            else:
                hi = max(lo, guess - 1)
                message = f"Too high. New range ends below {guess}"
                _render()

    api.hardware.set_led("yellow", True)
    api.hardware.set_led("green", True)
    api.hardware.set_led("blue", True)
    sub_id = api.event_bus.subscribe("input.button.pressed", on_button)
    try:
        _render()
        while not stop_event.is_set():
            stop_event.wait(0.25)
    finally:
        api.event_bus.unsubscribe(sub_id)
        api.hardware.set_led("yellow", False)
        api.hardware.set_led("green", False)
        api.hardware.set_led("blue", False)
