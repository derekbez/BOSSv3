"""Runtime state models and enumerations."""

from __future__ import annotations

from enum import Enum


class LedColor(str, Enum):
    """Colours available for the four colour-coded LEDs."""

    RED = "red"
    YELLOW = "yellow"
    GREEN = "green"
    BLUE = "blue"


class ButtonColor(str, Enum):
    """Colours available for the four colour-coded buttons."""

    RED = "red"
    YELLOW = "yellow"
    GREEN = "green"
    BLUE = "blue"
