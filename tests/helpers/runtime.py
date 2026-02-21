"""Test helpers — async wait utility."""

from __future__ import annotations

import asyncio
from typing import Callable


async def wait_for(
    condition: Callable[[], bool],
    timeout: float = 5.0,
    interval: float = 0.05,
) -> None:
    """Async poll *condition* every *interval* seconds, raising
    :class:`TimeoutError` if it doesn't become truthy within *timeout*.
    """
    elapsed = 0.0
    while not condition():
        if elapsed >= timeout:
            raise TimeoutError(
                f"Condition not met within {timeout}s"
            )
        await asyncio.sleep(interval)
        elapsed += interval
