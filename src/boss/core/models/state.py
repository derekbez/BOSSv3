"""Runtime state models and enumerations."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


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


class AppStatus(str, Enum):
    """Lifecycle status of a mini-app."""

    IDLE = "idle"
    LAUNCHING = "launching"
    RUNNING = "running"
    FINISHED = "finished"
    ERROR = "error"
    TIMED_OUT = "timed_out"


class HardwareState(BaseModel):
    """Snapshot of all hardware I/O state — used by ``HardwareEventBridge``
    for LED-gated button logic and by the UI for status display.
    """

    led_states: dict[LedColor, bool] = Field(
        default_factory=lambda: {c: False for c in LedColor},
    )
    switch_value: int = Field(default=0, ge=0, le=255)
    display_value: int | None = Field(default=None)
    active_app: str | None = Field(default=None)
    app_status: AppStatus = Field(default=AppStatus.IDLE)
