"""Tests for event subscription cleanup (Bug #3).

Verifies that subscriptions can be properly tracked and bulk-unsubscribed,
which is the mechanism used by layout.py and dev_panel.py to clean up
on client disconnect.
"""

from __future__ import annotations

import pytest

from boss.core.event_bus import EventBus
from boss.core.models.event import Event


@pytest.fixture
async def bus():
    b = EventBus(queue_size=100)
    await b.start()
    yield b
    await b.stop()


class TestSubscriptionCleanup:
    """Verify the subscribe-track-unsubscribe pattern works correctly."""

    async def test_tracked_unsubscribe_removes_all(self, bus: EventBus):
        """Subscribing with tracked IDs and unsubscribing all should leave no handlers."""
        call_count = 0

        async def handler(event: Event) -> None:
            nonlocal call_count
            call_count += 1

        # Simulate what layout.py now does: track sub IDs
        sub_ids = []
        sub_ids.append(bus.subscribe("test.event.a", handler))
        sub_ids.append(bus.subscribe("test.event.b", handler))
        sub_ids.append(bus.subscribe("test.event.c", handler))

        # Fire events — all 3 should trigger
        await bus.publish("test.event.a")
        await bus.publish("test.event.b")
        await bus.publish("test.event.c")
        import asyncio
        await asyncio.sleep(0.1)
        assert call_count == 3

        # Simulate disconnect cleanup
        for sid in sub_ids:
            bus.unsubscribe(sid)

        # Fire again — should not trigger
        call_count = 0
        await bus.publish("test.event.a")
        await bus.publish("test.event.b")
        await bus.publish("test.event.c")
        await asyncio.sleep(0.1)
        assert call_count == 0

    async def test_double_unsubscribe_is_safe(self, bus: EventBus):
        """Unsubscribing the same ID twice should not raise."""
        async def handler(event: Event) -> None:
            pass

        sub_id = bus.subscribe("test.event", handler)
        bus.unsubscribe(sub_id)
        bus.unsubscribe(sub_id)  # Should not raise

    async def test_multiple_page_renders_accumulate_without_cleanup(self, bus: EventBus):
        """Simulates the old bug: multiple subscribes without unsubscribe create duplicates."""
        call_count = 0

        async def handler(event: Event) -> None:
            nonlocal call_count
            call_count += 1

        # Simulate 3 page renders without cleanup (the old bug)
        for _ in range(3):
            bus.subscribe("test.event", handler)

        await bus.publish("test.event")
        import asyncio
        await asyncio.sleep(0.1)
        # With the bug, handler fires 3 times for one event
        assert call_count == 3

    async def test_cleanup_between_renders_prevents_accumulation(self, bus: EventBus):
        """With proper cleanup, re-rendering the page should not accumulate handlers."""
        call_count = 0

        async def handler(event: Event) -> None:
            nonlocal call_count
            call_count += 1

        # Simulate 3 page renders WITH cleanup (the fix)
        for _ in range(3):
            sub_ids = []
            sub_ids.append(bus.subscribe("test.event", handler))
            # Simulate disconnect: unsubscribe all
            for sid in sub_ids:
                bus.unsubscribe(sid)

        # Final subscribe (current page)
        bus.subscribe("test.event", handler)

        await bus.publish("test.event")
        import asyncio
        await asyncio.sleep(0.1)
        # Only one handler should fire
        assert call_count == 1
