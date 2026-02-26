"""Test helpers — wait utilities (async and sync)."""

from __future__ import annotations

import asyncio
import time
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


def wait_for_sync(
    condition: Callable[[], bool],
    timeout: float = 5.0,
    interval: float = 0.05,
) -> None:
    """Synchronous poll *condition* every *interval* seconds.

    Raises :class:`TimeoutError` if *condition* doesn't become truthy
    within *timeout* seconds.  Suitable for threaded / non-async tests.
    """
    deadline = time.monotonic() + timeout
    while not condition():
        if time.monotonic() >= deadline:
            raise TimeoutError(
                f"Condition not met within {timeout}s"
            )
        time.sleep(interval)
