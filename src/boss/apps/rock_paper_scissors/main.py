"""Rock Paper Scissors — best-of-five against random CPU.

Yellow = Rock, Green = Paper, Blue = Scissors.
"""

from __future__ import annotations

import random
import threading
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from boss.core.app_api import AppAPI


CHOICES = ["Rock", "Paper", "Scissors"]


def _result(player: str, cpu: str) -> str:
    if player == cpu:
        return "draw"
    wins = {
        ("Rock", "Scissors"),
        ("Paper", "Rock"),
        ("Scissors", "Paper"),
    }
    return "win" if (player, cpu) in wins else "loss"


def run(stop_event: threading.Event, api: "AppAPI") -> None:
    rounds_target = int(api.get_app_config().get("rounds", 5))
    if rounds_target < 1:
        rounds_target = 5

    wins = 0
    losses = 0
    draws = 0
    rounds = 0
    last_msg = "Choose your move"

    def _render() -> None:
        api.screen.clear()
        api.screen.display_text(
            (
                "Rock Paper Scissors\n\n"
                f"Round: {rounds}/{rounds_target}\n"
                f"W/L/D: {wins}/{losses}/{draws}\n\n"
                f"{last_msg}\n\n"
                "[YEL] Rock  [GRN] Paper  [BLU] Scissors"
            ),
            align="left",
            font_size=18,
        )

    def _reset_series() -> None:
        nonlocal wins, losses, draws, rounds, last_msg
        wins = 0
        losses = 0
        draws = 0
        rounds = 0
        last_msg = "New best-of-five series started"
        _render()

    def _play(player_choice: str) -> None:
        nonlocal wins, losses, draws, rounds, last_msg
        cpu = random.choice(CHOICES)
        outcome = _result(player_choice, cpu)
        rounds += 1
        if outcome == "win":
            wins += 1
            last_msg = f"You: {player_choice} vs CPU: {cpu} — ✅ Win"
        elif outcome == "loss":
            losses += 1
            last_msg = f"You: {player_choice} vs CPU: {cpu} — ❌ Loss"
        else:
            draws += 1
            last_msg = f"You: {player_choice} vs CPU: {cpu} — ➖ Draw"

        if rounds >= rounds_target:
            if wins > losses:
                last_msg += "\nSeries result: YOU WIN"
            elif wins < losses:
                last_msg += "\nSeries result: CPU WINS"
            else:
                last_msg += "\nSeries result: DRAW"
            _render()
            stop_event.wait(1.2)
            if not stop_event.is_set():
                _reset_series()
        else:
            _render()

    def on_button(event: Any) -> None:
        payload = event.payload or {}
        btn = payload.get("button")
        if btn == "yellow":
            _play("Rock")
        elif btn == "green":
            _play("Paper")
        elif btn == "blue":
            _play("Scissors")

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
