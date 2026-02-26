"""Coin Flip Streak — guess heads/tails and track streak.

Yellow = heads, Blue = tails, Green = flip.
"""

from __future__ import annotations

import random
import threading
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from boss.core.app_api import AppAPI


def run(stop_event: threading.Event, api: "AppAPI") -> None:
    streak = 0
    best = 0
    rounds = 0
    pending_guess: str | None = None
    message = "Pick HEADS (yellow) or TAILS (blue), then press GREEN"

    def _render() -> None:
        guess_text = pending_guess if pending_guess else "none"
        api.screen.clear()
        api.screen.display_text(
            (
                "Coin Flip Streak\n\n"
                f"Current streak: {streak}\n"
                f"Best streak: {best}\n"
                f"Rounds: {rounds}\n"
                f"Guess: {guess_text}\n\n"
                f"{message}\n\n"
                "[YEL] Heads  [GRN] Flip  [BLU] Tails"
            ),
            align="left",
            font_size=18,
        )

    def on_button(event: Any) -> None:
        nonlocal pending_guess, streak, best, rounds, message
        payload = event.payload or {}
        btn = payload.get("button")
        if btn == "yellow":
            pending_guess = "Heads"
            message = "Guess locked: Heads"
            _render()
        elif btn == "blue":
            pending_guess = "Tails"
            message = "Guess locked: Tails"
            _render()
        elif btn == "green":
            if pending_guess is None:
                message = "Pick Heads/Tails first"
                _render()
                return
            result = random.choice(["Heads", "Tails"])
            rounds += 1
            if result == pending_guess:
                streak += 1
                best = max(best, streak)
                message = f"✅ {result}! Correct guess."
            else:
                streak = 0
                message = f"❌ {result}! Streak reset."
            pending_guess = None
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
