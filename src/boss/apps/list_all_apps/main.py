"""List All Apps — paginated table of switch → app mappings.

Yellow = prev page, Blue = next page.
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Any

from boss.apps._lib.paginator import TextPaginator


if TYPE_CHECKING:
    from boss.core.app_api import AppAPI


def run(stop_event: threading.Event, api: "AppAPI") -> None:
    api.log_info("list_all_apps starting")
    cfg = api.get_app_config()
    per_page = int(cfg.get("entries_per_page", 15))

    summaries = api.get_all_app_summaries()
    if not summaries:
        api.screen.clear()
        api.screen.display_text("No apps mapped.", align="center")
        stop_event.wait(5)
        return

    lines: list[str] = []
    for s in summaries:
        num = str(s["switch"]).rjust(3)
        name = s["name"]
        desc = s.get("description", "")
        label = f"{num}  {name}"
        if desc:
            label += f" — {desc}"
        lines.append(label)

    def _led_update(color: str, on: bool) -> None:
        api.hardware.set_led(color, on)

    paginator = TextPaginator(
        lines, per_page=per_page, led_update=_led_update,
        prev_color="yellow", next_color="blue",
    )

    def _render() -> None:
        page_lines = paginator.page_lines()
        header = f"Apps  (page {paginator.page + 1}/{paginator.total_pages})"
        body = "\n".join(page_lines) if page_lines else "(empty)"
        footer = "[YEL] Prev   [BLU] Next"
        api.screen.clear()
        api.screen.display_text(
            f"{header}\n\n{body}\n\n{footer}", font_size=16, align="left",
        )

    def on_button(event: Any) -> None:
        button = event.payload.get("button")
        if button == "yellow":
            if paginator.prev():
                _render()
        elif button == "blue":
            if paginator.next():
                _render()

    sub_id = api.event_bus.subscribe("input.button.pressed", on_button)
    try:
        _render()
        while not stop_event.is_set():
            stop_event.wait(0.5)
    finally:
        api.event_bus.unsubscribe(sub_id)
        api.hardware.set_led("yellow", False)
        api.hardware.set_led("blue", False)
        api.log_info("list_all_apps stopping")
