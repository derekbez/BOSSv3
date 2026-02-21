"""Pydantic model for event bus messages."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class Event(BaseModel):
    """Structured event flowing through the async event bus."""

    event_type: str = Field(description="Dot-separated event type, e.g. 'input.button.pressed'")
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
