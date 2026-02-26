"""Public Domain Book Snippet — contiguous passages from local .txt assets with pagination.

Yellow = prev page, Green = new passage, Blue = next page.
"""

from __future__ import annotations

import random
import time
from pathlib import Path
import threading
from typing import TYPE_CHECKING, Any

from boss.apps._lib.paginator import TextPaginator, wrap_paragraphs


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


def _pick_contiguous(all_lines: list[str], n: int) -> list[str]:
    """Pick *n* contiguous lines starting from a random position."""
    if len(all_lines) <= n:
        return list(all_lines)
    start = random.randint(0, len(all_lines) - n)
    return all_lines[start : start + n]


if TYPE_CHECKING:
    from boss.core.app_api import AppAPI


def run(stop_event: threading.Event, api: "AppAPI") -> None:
    cfg = api.get_app_config()
    n_lines = int(cfg.get("lines", 20))
    shuffle_sec = float(cfg.get("shuffle_seconds", 600))
    per_page = int(cfg.get("lines_per_page", 10))

    assets_dir = api.get_app_path() / "assets"
    all_lines = _load_texts(assets_dir)
    if not all_lines:
        api.screen.clear()
        api.screen.display_text("Book Snippet\n\n(no text files in assets/)", align="left")
        stop_event.wait(5)
        return

    last_shuffle = 0.0

    def _led(color: str, on: bool) -> None:
        api.hardware.set_led(color, on)

    paginator = TextPaginator([], per_page, led_update=_led)

    def _render() -> None:
        page_lines = paginator.page_lines()
        body = "\n".join(page_lines) if page_lines else "(no data)"
        pg = f"({paginator.page + 1}/{paginator.total_pages})"
        api.screen.clear()
        api.screen.display_text(
            f"Book Snippet {pg}\n\n{body}",
            font_size=16,
            align="left",
        )

    def _refresh() -> None:
        passage = _pick_contiguous(all_lines, n_lines)
        lines = wrap_paragraphs(passage, width=90, sep_blank=False)
        paginator.set_lines(lines)
        paginator.reset()
        _render()

    def on_button(event: Any) -> None:
        nonlocal last_shuffle
        btn = event.payload.get("button")
        if btn == "green":
            last_shuffle = time.time()
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
        last_shuffle = time.time()
        while not stop_event.is_set():
            if time.time() - last_shuffle >= shuffle_sec:
                last_shuffle = time.time()
                _refresh()
            stop_event.wait(0.5)
    finally:
        api.event_bus.unsubscribe(sub_id)
        api.hardware.set_led("green", False)
        api.hardware.set_led("yellow", False)
        api.hardware.set_led("blue", False)
