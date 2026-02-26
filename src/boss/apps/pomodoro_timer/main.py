"""Pomodoro Timer — configurable work/break timer.

Green = start/pause, Yellow = short break, Blue = long break.
"""

from __future__ import annotations

import threading
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from boss.core.app_api import AppAPI


def _fmt_mmss(seconds: int) -> str:
    minutes, secs = divmod(max(0, int(seconds)), 60)
    return f"{minutes:02d}:{secs:02d}"


def run(stop_event: threading.Event, api: "AppAPI") -> None:
    cfg = api.get_app_config()
    work_minutes = int(cfg.get("work_minutes", 25))
    short_break_minutes = int(cfg.get("short_break_minutes", 5))
    long_break_minutes = int(cfg.get("long_break_minutes", 15))
    long_break_every = int(cfg.get("long_break_every", 4))

    work_seconds = max(60, work_minutes * 60)
    short_break_seconds = max(60, short_break_minutes * 60)
    long_break_seconds = max(60, long_break_minutes * 60)
    long_break_every = max(2, long_break_every)

    phase = "Work"
    remaining = work_seconds
    running = False
    completed_work_sessions = 0
    message = "Press GREEN to start"
    last_tick = time.time()

    def _set_phase(new_phase: str) -> None:
        nonlocal phase, remaining, message
        phase = new_phase
        if phase == "Work":
            remaining = work_seconds
        elif phase == "Short Break":
            remaining = short_break_seconds
        else:
            remaining = long_break_seconds
        message = f"Switched to {phase}"

    def _render() -> None:
        status = "Running" if running else "Paused"
        api.screen.clear()
        api.screen.display_text(
            (
                "Pomodoro Timer\n\n"
                f"Phase: {phase}\n"
                f"Time: {_fmt_mmss(remaining)}\n"
                f"Status: {status}\n"
                f"Work sessions: {completed_work_sessions}\n\n"
                f"{message}\n\n"
                "[YEL] Short break  [GRN] Start/Pause  [BLU] Long break"
            ),
            align="left",
            font_size=20,
        )

    def _handle_finished_phase() -> None:
        nonlocal completed_work_sessions
        if phase == "Work":
            completed_work_sessions += 1
            if completed_work_sessions % long_break_every == 0:
                _set_phase("Long Break")
            else:
                _set_phase("Short Break")
        else:
            _set_phase("Work")

    def on_button(event: Any) -> None:
        nonlocal running, message
        payload = event.payload or {}
        btn = payload.get("button")
        if btn == "green":
            running = not running
            message = "Started" if running else "Paused"
            _render()
        elif btn == "yellow":
            running = False
            _set_phase("Short Break")
            _render()
        elif btn == "blue":
            running = False
            _set_phase("Long Break")
            _render()

    api.hardware.set_led("yellow", True)
    api.hardware.set_led("green", True)
    api.hardware.set_led("blue", True)
    sub_id = api.event_bus.subscribe("input.button.pressed", on_button)
    try:
        _render()
        while not stop_event.is_set():
            now = time.time()
            if running and now - last_tick >= 1.0:
                elapsed = int(now - last_tick)
                if elapsed > 0:
                    remaining = max(0, remaining - elapsed)
                    last_tick = now
                    if remaining == 0:
                        running = False
                        _handle_finished_phase()
                    _render()
            else:
                if not running:
                    last_tick = now
                stop_event.wait(0.2)
    finally:
        api.event_bus.unsubscribe(sub_id)
        api.hardware.set_led("yellow", False)
        api.hardware.set_led("green", False)
        api.hardware.set_led("blue", False)
