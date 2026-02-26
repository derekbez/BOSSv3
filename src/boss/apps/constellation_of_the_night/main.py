"""Constellation of the Night — visible constellations from your location.

Uses the ``ephem`` library to compute which bright stars are above the
horizon right now, groups them by constellation, and displays the most
prominent ones with altitude and compass direction.  Green = refresh.
"""

from __future__ import annotations

import math
import time
import threading
from typing import TYPE_CHECKING, Any

import ephem


if TYPE_CHECKING:
    from boss.core.app_api import AppAPI

# A curated set of bright, well-known navigational / naked-eye stars.
_STAR_NAMES: list[str] = [
    "Sirius", "Canopus", "Arcturus", "Vega", "Capella",
    "Rigel", "Procyon", "Betelgeuse", "Altair", "Aldebaran",
    "Spica", "Antares", "Pollux", "Fomalhaut", "Deneb",
    "Regulus", "Castor", "Bellatrix", "Alnilam", "Polaris",
    "Mizar", "Dubhe", "Alkaid", "Mirfak", "Alpheratz",
    "Hamal", "Denebola", "Nunki", "Rasalhague", "Kochab",
]


def _az_to_compass(az_deg: float) -> str:
    """Convert azimuth in degrees to an 8-point compass direction."""
    dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    idx = round(az_deg / 45) % 8
    return dirs[idx]


def _get_visible_constellations(
    lat: float, lon: float, min_alt: float = 10.0,
) -> list[dict[str, str | float]]:
    """Return constellations with at least one star above *min_alt* degrees.

    Each entry: ``{"name": "Orion", "abbr": "Ori", "alt": 42.3, "dir": "SE"}``.
    Sorted by peak altitude descending.
    """
    obs = ephem.Observer()
    obs.lat = str(lat)
    obs.lon = str(lon)
    obs.date = ephem.now()

    # Track the brightest/highest star per constellation
    constellations: dict[str, dict[str, str | float]] = {}

    for star_name in _STAR_NAMES:
        try:
            star = ephem.star(star_name)
        except KeyError:
            continue
        star.compute(obs)
        alt_deg = math.degrees(star.alt)
        if alt_deg < min_alt:
            continue
        az_deg = math.degrees(star.az)
        abbr, cname = ephem.constellation(star)
        if cname not in constellations or alt_deg > constellations[cname]["alt"]:
            constellations[cname] = {
                "name": cname,
                "abbr": abbr,
                "alt": round(alt_deg, 1),
                "dir": _az_to_compass(az_deg),
            }

    return sorted(constellations.values(), key=lambda c: c["alt"], reverse=True)


def run(stop_event: threading.Event, api: "AppAPI") -> None:
    cfg = api.get_app_config()
    refresh = float(cfg.get("refresh_seconds", 600))
    max_show = int(cfg.get("max_constellations", 8))
    title = "Night Sky"
    last_fetch = 0.0

    loc = api.get_global_location()
    lat, lon = loc["lat"], loc["lon"]

    def _show() -> None:
        try:
            visible = _get_visible_constellations(lat, lon)
            if not visible:
                api.screen.clear()
                api.screen.display_text(
                    f"{title}\n\nNo constellations above the horizon\n"
                    "(check back after dark!)",
                    align="left",
                )
                return
            lines: list[str] = []
            for c in visible[:max_show]:
                lines.append(f"  {c['name']:20s} {c['alt']:4.0f}° {c['dir']}")
            body = "\n".join(lines)
            api.screen.clear()
            api.screen.display_text(
                f"{title}\n\n{body}", font_size=16, align="left",
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
