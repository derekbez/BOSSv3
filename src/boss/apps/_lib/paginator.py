"""Shared text-wrapping and pagination utilities for mini-apps.

Ported from BOSSv2's ``boss.ui.text.utils`` — provides deterministic
wrapping so apps can control line layout, plus a ``TextPaginator`` with
LED-aware navigation.
"""

from __future__ import annotations

import textwrap
from typing import Callable, Iterable


def wrap_plain(text: str, width: int) -> list[str]:
    """Wrap a single block of text into lines."""
    return textwrap.wrap(text, width=width) or [text]


def wrap_with_prefix(text: str, prefix: str, width: int) -> list[str]:
    """Wrap a paragraph so first line has *prefix* and following lines align."""
    body_width = max(10, width - len(prefix))
    raw = textwrap.wrap(text, width=body_width) or [text]
    out: list[str] = []
    for i, seg in enumerate(raw):
        if i == 0:
            out.append(prefix + seg)
        else:
            out.append(" " * len(prefix) + seg)
    return out


def wrap_events(events: Iterable[tuple[str, str]], width: int) -> list[str]:
    """Wrap ``(year, description)`` pairs into display lines."""
    lines: list[str] = []
    for year, desc in events:
        prefix = f"{year}: "
        lines.extend(wrap_with_prefix(desc, prefix, width))
    return lines


def wrap_paragraphs(
    paragraphs: Iterable[str], width: int, sep_blank: bool = True
) -> list[str]:
    """Wrap multiple paragraphs preserving blank-line separation."""
    out: list[str] = []
    first = True
    for p in paragraphs:
        p = (p or "").strip()
        if not p:
            continue
        if not first and sep_blank:
            out.append("")
        out.extend(wrap_plain(p, width))
        first = False
    return out


class TextPaginator:
    """Page through pre-wrapped lines with optional LED callback.

    Args:
        lines: The full list of text lines.
        per_page: How many lines per page.
        led_update: ``(color, on)`` callable for navigation LEDs.
        prev_color: LED colour for "has previous page".
        next_color: LED colour for "has next page".
    """

    def __init__(
        self,
        lines: list[str],
        per_page: int,
        led_update: Callable[[str, bool], None] | None = None,
        prev_color: str = "yellow",
        next_color: str = "blue",
    ) -> None:
        self._lines = lines
        self._per_page = max(1, per_page)
        self._page = 0
        self._led_update = led_update
        self._prev_color = prev_color
        self._next_color = next_color
        self._update_leds()

    # ---- Data mutation --------------------------------------------------

    def set_lines(self, lines: list[str]) -> None:
        self._lines = lines
        if self._page >= self.total_pages:
            self._page = max(0, self.total_pages - 1)
        self._update_leds()

    # ---- Properties -----------------------------------------------------

    @property
    def page(self) -> int:
        return self._page

    @property
    def total_pages(self) -> int:
        if not self._lines:
            return 1
        return (len(self._lines) - 1) // self._per_page + 1

    def has_prev(self) -> bool:
        return self._page > 0

    def has_next(self) -> bool:
        return self._page < self.total_pages - 1

    # ---- Navigation -----------------------------------------------------

    def next(self) -> bool:
        if self.has_next():
            self._page += 1
            self._update_leds()
            return True
        return False

    def prev(self) -> bool:
        if self.has_prev():
            self._page -= 1
            self._update_leds()
            return True
        return False

    def reset(self) -> None:
        self._page = 0
        self._update_leds()

    # ---- Data access ----------------------------------------------------

    def page_lines(self) -> list[str]:
        if not self._lines:
            return []
        start = self._page * self._per_page
        end = start + self._per_page
        return self._lines[start:end]

    # ---- Internal -------------------------------------------------------

    def _update_leds(self) -> None:
        if self._led_update:
            self._led_update(self._prev_color, self.has_prev())
            self._led_update(self._next_color, self.has_next())
