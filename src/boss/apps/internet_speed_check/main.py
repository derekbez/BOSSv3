"""Internet Speed Check — real download/upload test.  Green = retest."""

from __future__ import annotations

import time
import threading
from typing import TYPE_CHECKING, Any

import speedtest


if TYPE_CHECKING:
    from boss.core.app_api import AppAPI


def _run_test() -> dict[str, float]:
    """Run a speed test and return download/upload in Mbps and ping in ms."""
    st = speedtest.Speedtest()
    st.get_best_server()
    download = st.download() / 1_000_000  # bits → Mbps
    upload = st.upload() / 1_000_000
    ping = st.results.ping
    return {"download": download, "upload": upload, "ping": ping}


def run(stop_event: threading.Event, api: "AppAPI") -> None:
    cfg = api.get_app_config()
    refresh = float(cfg.get("refresh_seconds", 1800))
    title = "Net Speed"
    last_fetch = 0.0

    def _show() -> None:
        try:
            api.screen.clear()
            api.screen.display_text(f"{title}\n\nTesting…", align="left")
            result = _run_test()
            api.screen.clear()
            api.screen.display_text(
                f"{title}\n\n"
                f"Down {result['download']:.1f} Mbps\n"
                f"Up   {result['upload']:.1f} Mbps\n"
                f"Ping {result['ping']:.0f} ms",
                align="left",
            )
        except Exception as exc:
            api.screen.clear()
            api.screen.display_text(f"{title}\n\nErr: {exc}", align="left")

    def on_button(event: Any) -> None:
        nonlocal last_fetch
        if event.payload.get("button") == "green":
            last_fetch = time.time()
            _show()

    api.hardware.set_led("green", True)
    sub_id = api.event_bus.subscribe("input.button.pressed", on_button)
    try:
        _show()
        last_fetch = time.time()
        while not stop_event.is_set():
            if time.time() - last_fetch >= refresh:
                last_fetch = time.time()
                _show()
            stop_event.wait(0.5)
    finally:
        api.event_bus.unsubscribe(sub_id)
        api.hardware.set_led("green", False)
