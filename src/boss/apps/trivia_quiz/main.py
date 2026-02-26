"""Trivia Quiz — 3-choice trivia from Open Trivia DB.

Yellow/Green/Blue = answer choices A/B/C.
"""

from __future__ import annotations

import html
import random
import threading
import time
from typing import TYPE_CHECKING, Any

from boss.apps._lib.http_helpers import fetch_json
from boss.apps._lib.paginator import wrap_paragraphs

API_URL = "https://opentdb.com/api.php"


if TYPE_CHECKING:
    from boss.core.app_api import AppAPI


def _fetch_question(category: str, difficulty: str, timeout: float) -> tuple[str, list[str], int]:
    params = {
        "amount": "1",
        "type": "multiple",
    }
    if category and category != "any":
        params["category"] = category
    if difficulty and difficulty != "any":
        params["difficulty"] = difficulty

    data = fetch_json(API_URL, params=params, timeout=timeout)
    results = data.get("results", [])
    if not results:
        raise RuntimeError("No trivia question returned")

    q = results[0]
    question = html.unescape(str(q.get("question", "?")))
    correct = html.unescape(str(q.get("correct_answer", "")))
    incorrect = [html.unescape(str(x)) for x in q.get("incorrect_answers", [])]

    if not correct or len(incorrect) < 2:
        raise RuntimeError("Incomplete trivia answers")

    options = [correct] + incorrect[:2]
    random.shuffle(options)
    correct_idx = options.index(correct)

    return question, options, correct_idx


def run(stop_event: threading.Event, api: "AppAPI") -> None:
    cfg = api.get_app_config()
    category = str(cfg.get("category", "any"))
    difficulty = str(cfg.get("difficulty", "any"))
    refresh = float(cfg.get("refresh_seconds", 600))
    timeout = float(cfg.get("request_timeout_seconds", 6))

    score = 0
    total = 0
    last_fetch = 0.0

    current_question = ""
    current_options: list[str] = []
    current_correct = -1
    feedback = ""

    def _render() -> None:
        wrapped_q = wrap_paragraphs([current_question], width=94, sep_blank=False)
        q_block = "\n".join(wrapped_q)
        lines = [
            f"Trivia Quiz   Score: {score}/{total}",
            "",
            q_block,
            "",
            f"[YEL] A: {current_options[0] if len(current_options) > 0 else '?'}",
            f"[GRN] B: {current_options[1] if len(current_options) > 1 else '?'}",
            f"[BLU] C: {current_options[2] if len(current_options) > 2 else '?'}",
        ]
        if feedback:
            lines.extend(["", feedback])
        api.screen.clear()
        api.screen.display_text("\n".join(lines), align="left", font_size=16)

    def _next_question() -> None:
        nonlocal current_question, current_options, current_correct, feedback
        try:
            q, opts, correct_idx = _fetch_question(category, difficulty, timeout)
            current_question = q
            current_options = opts
            current_correct = correct_idx
            feedback = ""
        except Exception as exc:
            current_question = "Trivia unavailable"
            current_options = ["Try again", "Try again", "Try again"]
            current_correct = -1
            feedback = f"Err: {exc}"
        _render()

    def _answer(choice_idx: int) -> None:
        nonlocal score, total, feedback, last_fetch
        if current_correct < 0:
            last_fetch = time.time()
            _next_question()
            return
        total += 1
        if choice_idx == current_correct:
            score += 1
            feedback = "✅ Correct!"
        else:
            correct_letter = ["A", "B", "C"][current_correct]
            correct_text = current_options[current_correct]
            feedback = f"❌ Incorrect. {correct_letter}: {correct_text}"
        _render()
        last_fetch = time.time()
        stop_event.wait(1.2)
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
        last_fetch = time.time()
        while not stop_event.is_set():
            if time.time() - last_fetch >= refresh:
                last_fetch = time.time()
                _next_question()
            stop_event.wait(0.25)
    finally:
        api.event_bus.unsubscribe(sub_id)
        api.hardware.set_led("yellow", False)
        api.hardware.set_led("green", False)
        api.hardware.set_led("blue", False)
