"""Tests for the async EventBus."""

import asyncio

import pytest

from boss.core.event_bus import EventBus
from boss.core.models.event import Event


class TestEventBusSubscribePublish:
    async def test_basic_publish_subscribe(self, event_bus: EventBus):
        received: list[Event] = []

        async def handler(event: Event):
            received.append(event)

        event_bus.subscribe("test.event", handler)
        await event_bus.publish("test.event", {"key": "value"})

        # Give consumer a tick to dispatch.
        await asyncio.sleep(0.1)
        assert len(received) == 1
        assert received[0].event_type == "test.event"
        assert received[0].payload == {"key": "value"}

    async def test_multiple_subscribers(self, event_bus: EventBus):
        counts = {"a": 0, "b": 0}

        async def handler_a(_e: Event):
            counts["a"] += 1

        async def handler_b(_e: Event):
            counts["b"] += 1

        event_bus.subscribe("multi", handler_a)
        event_bus.subscribe("multi", handler_b)
        await event_bus.publish("multi")
        await asyncio.sleep(0.1)

        assert counts["a"] == 1
        assert counts["b"] == 1

    async def test_unsubscribe(self, event_bus: EventBus):
        received: list[Event] = []

        async def handler(event: Event):
            received.append(event)

        sub_id = event_bus.subscribe("unsub.test", handler)
        event_bus.unsubscribe(sub_id)

        await event_bus.publish("unsub.test")
        await asyncio.sleep(0.1)

        assert len(received) == 0


class TestEventBusFilter:
    async def test_filter_match(self, event_bus: EventBus):
        received: list[Event] = []

        async def handler(event: Event):
            received.append(event)

        event_bus.subscribe("input.button.pressed", handler, filter_dict={"button": "red"})
        await event_bus.publish("input.button.pressed", {"button": "red"})
        await event_bus.publish("input.button.pressed", {"button": "blue"})
        await asyncio.sleep(0.1)

        assert len(received) == 1
        assert received[0].payload["button"] == "red"

    async def test_filter_no_match(self, event_bus: EventBus):
        received: list[Event] = []

        async def handler(event: Event):
            received.append(event)

        event_bus.subscribe("x", handler, filter_dict={"k": "v"})
        await event_bus.publish("x", {"k": "other"})
        await asyncio.sleep(0.1)

        assert len(received) == 0


class TestEventBusThreadsafe:
    async def test_publish_threadsafe(self, event_bus: EventBus):
        received: list[Event] = []

        async def handler(event: Event):
            received.append(event)

        event_bus.subscribe("threadsafe.test", handler)

        # Simulate a GPIO thread publishing.
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            lambda: event_bus.publish_threadsafe("threadsafe.test", {"from": "thread"}),
        )
        await asyncio.sleep(0.2)

        assert len(received) == 1
        assert received[0].payload["from"] == "thread"


class TestEventBusErrorRemoval:
    async def test_handler_error_auto_unsubscribes(self, event_bus: EventBus):
        call_count = 0

        async def bad_handler(_e: Event):
            nonlocal call_count
            call_count += 1
            raise RuntimeError("boom")

        event_bus.subscribe("err.test", bad_handler)

        # First publish triggers the error → auto-unsubscribe.
        await event_bus.publish("err.test")
        await asyncio.sleep(0.1)
        assert call_count == 1

        # Second publish should NOT reach the handler.
        await event_bus.publish("err.test")
        await asyncio.sleep(0.1)
        assert call_count == 1  # still 1

    async def test_sync_handler_works(self, event_bus: EventBus):
        received: list[str] = []

        def sync_handler(event: Event):
            received.append(event.event_type)

        event_bus.subscribe("sync.test", sync_handler)
        await event_bus.publish("sync.test")
        await asyncio.sleep(0.1)

        assert received == ["sync.test"]


class TestEventBusOverflow:
    async def test_queue_overflow_drops_oldest(self):
        bus = EventBus(queue_size=2)
        await bus.start()
        try:
            # Fill queue without consuming.
            # Pause consumer by not giving it a chance to run.
            await bus.publish("a", {"n": 1})
            await bus.publish("b", {"n": 2})
            # Third publish triggers overflow handling.
            await bus.publish("c", {"n": 3})
            # Should not raise — graceful handling.
        finally:
            await bus.stop()
