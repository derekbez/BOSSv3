"""Math Challenge — 3-choice arithmetic quiz.

Yellow/Green/Blue = options A/B/C.
"""

from __future__ import annotations

import random
import threading
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from boss.core.app_api import AppAPI


def _make_question(operations: list[str], max_number: int) -> tuple[str, list[int], int]:
    op = random.choice(operations)
    a = random.randint(1, max_number)
    b = random.randint(1, max_number)

    if op == "+":
        answer = a + b
    elif op == "-":
        if b > a:
            a, b = b, a
        answer = a - b
    else:  # "*"
        a = random.randint(1, max(2, max_number // 4))
        b = random.randint(1, max(2, max_number // 4))
        answer = a * b

    question = f"{a} {op} {b} = ?"
    wrongs: set[int] = set()
    while len(wrongs) < 2:
        delta = random.randint(1, max(2, max_number // 5))
        candidate = answer + random.choice([-delta, delta])
        if candidate != answer and candidate >= 0:
            wrongs.add(candidate)

    options = [answer, *wrongs]
    random.shuffle(options)
    correct_idx = options.index(answer)
    return question, options, correct_idx


def run(stop_event: threading.Event, api: "AppAPI") -> None:
    cfg = api.get_app_config()
    ops = [x for x in cfg.get("operations", ["+", "-", "*"]) if x in {"+", "-", "*"}]
    if not ops:
        ops = ["+", "-", "*"]
    max_number = int(cfg.get("max_number", 100))
    if max_number < 5:
        max_number = 100

    score = 0
    streak = 0
    total = 0
    question = ""
    options: list[int] = []
    correct_idx = -1
    feedback = ""

    def _render() -> None:
        api.screen.clear()
        api.screen.display_text(
            (
                "Math Challenge\n\n"
                f"Score: {score}/{total}   Streak: {streak}\n"
                f"Question: {question}\n\n"
                f"[YEL] A: {options[0] if len(options) > 0 else '?'}\n"
                f"[GRN] B: {options[1] if len(options) > 1 else '?'}\n"
                f"[BLU] C: {options[2] if len(options) > 2 else '?'}"
                + (f"\n\n{feedback}" if feedback else "")
            ),
            align="left",
            font_size=18,
        )

    def _next_question() -> None:
        nonlocal question, options, correct_idx, feedback
        question, options, correct_idx = _make_question(ops, max_number)
        feedback = ""
        _render()

    def _answer(choice: int) -> None:
        nonlocal score, total, streak, feedback
        if correct_idx < 0:
            return
        total += 1
        if choice == correct_idx:
            score += 1
            streak += 1
            feedback = "✅ Correct"
        else:
            streak = 0
            feedback = f"❌ Incorrect (answer: {options[correct_idx]})"
        _render()
        stop_event.wait(1.0)
        if not stop_event.is_set():
            _next_question()

    def on_button(event: Any) -> None:
        payload = event.payload or {}
        btn = payload.get("button")
        if btn == "yellow":
            _answer(0)
        elif btn == "green":
            _answer(1)
        elif btn == "blue":
            _answer(2)

    api.hardware.set_led("yellow", True)
    api.hardware.set_led("green", True)
    api.hardware.set_led("blue", True)
    sub_id = api.event_bus.subscribe("input.button.pressed", on_button)
    try:
        _next_question()
        while not stop_event.is_set():
            stop_event.wait(0.25)
    finally:
        api.event_bus.unsubscribe(sub_id)
        api.hardware.set_led("yellow", False)
        api.hardware.set_led("green", False)
        api.hardware.set_led("blue", False)
