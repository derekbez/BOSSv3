"""Public Domain Book Snippet — random lines from local .txt assets.  Green = reshuffle."""

from __future__ import annotations

import random
import time
from pathlib import Path
from threading import Event
from typing import Any


def _load_texts(assets_dir: Path) -> list[str]:
    """Gather all non-empty lines from every .txt file in *assets_dir*."""
    lines: list[str] = []
    if not assets_dir.is_dir():
        return lines
    for txt in sorted(assets_dir.glob("*.txt")):
        try:
            lines.extend(
                line.rstrip()
                for line in txt.read_text(encoding="utf-8", errors="replace").splitlines()
                if line.strip()
            )
        except Exception:
            pass
    return lines


def run(stop_event: Event, api: Any) -> None:
    cfg = api.get_app_config()
    n_lines = int(cfg.get("lines", 5))
    shuffle_sec = float(cfg.get("shuffle_seconds", 600))

    assets_dir = api.get_app_path() / "assets"
    all_lines = _load_texts(assets_dir)
    if not all_lines:
        api.screen.clear()
        api.screen.display_text("Book Snippet\n\n(no text files in assets/)", align="left")
        stop_event.wait(5)
        return

    last_shuffle = 0.0

    def _show() -> None:
        sample = random.sample(all_lines, min(n_lines, len(all_lines)))
        api.screen.clear()
        api.screen.display_text("Book Snippet\n\n" + "\n".join(sample), font_size=16, align="left")

    def on_button(event: Any) -> None:
        nonlocal last_shuffle
        if event.payload.get("button") == "green":
            last_shuffle = time.time()
            _show()

    api.hardware.set_led("green", True)
    sub_id = api.event_bus.subscribe("input.button.pressed", on_button)
    try:
        _show()
        last_shuffle = time.time()
        while not stop_event.is_set():
            if time.time() - last_shuffle >= shuffle_sec:
                last_shuffle = time.time()
                _show()
            stop_event.wait(0.5)
    finally:
        api.event_bus.unsubscribe(sub_id)
        api.hardware.set_led("green", False)
