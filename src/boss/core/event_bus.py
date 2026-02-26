"""Async event bus — ``asyncio.Queue``-based pub/sub.

All handler dispatch runs on the NiceGUI / asyncio event loop.  GPIO
callback threads can publish safely via :meth:`EventBus.publish_threadsafe`.

Key behaviours:
* Handlers may be sync or async — sync handlers are run in the default
  thread-pool executor.
* A handler that raises is **auto-unsubscribed** (logged + removed).
* ``filter_dict`` on subscribe is AND-matched against the event payload.
* Bounded queue — on overflow the oldest event is dropped with a warning.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

from boss.core.models.event import Event

_log = logging.getLogger(__name__)


@dataclass
class _Subscription:
    sub_id: str
    event_type: str
    handler: Callable[..., Any]
    filter_dict: dict[str, Any] | None = None


class EventBus:
    """Async event bus backed by an :class:`asyncio.Queue`.

    Args:
        queue_size: Maximum number of events queued before overflow handling.
    """

    def __init__(self, queue_size: int = 1000) -> None:
        self._queue_size = queue_size
        self._queue: asyncio.Queue[Event] | None = None
        self._subscriptions: dict[str, _Subscription] = {}
        # event_type → [sub_id, …]  for fast dispatch lookup
        self._type_index: dict[str, list[str]] = {}
        self._consumer_task: asyncio.Task[None] | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start the background consumer task.  Must be called from an
        ``async`` context that already has a running event loop.
        """
        self._loop = asyncio.get_running_loop()
        self._queue = asyncio.Queue(maxsize=self._queue_size)
        self._consumer_task = asyncio.create_task(self._consume(), name="event-bus-consumer")
        _log.info("Event bus started (queue_size=%d)", self._queue_size)

    async def stop(self) -> None:
        """Cancel the consumer task and drain the queue."""
        if self._consumer_task is not None:
            self._consumer_task.cancel()
            try:
                await self._consumer_task
            except asyncio.CancelledError:
                pass
            self._consumer_task = None
        self._subscriptions.clear()
        self._type_index.clear()
        _log.info("Event bus stopped")

    # ------------------------------------------------------------------
    # Publish
    # ------------------------------------------------------------------

    async def publish(self, event_type: str, payload: dict[str, Any] | None = None) -> None:
        """Enqueue an event (call from async code on the event loop)."""
        event = Event(event_type=event_type, payload=payload or {})
        assert self._queue is not None, "EventBus.start() has not been called"
        try:
            self._queue.put_nowait(event)
        except asyncio.QueueFull:
            # Drop oldest to make room.
            try:
                self._queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
            _log.warning("Event bus queue overflow — dropped oldest event")
            self._queue.put_nowait(event)

    def publish_threadsafe(self, event_type: str, payload: dict[str, Any] | None = None) -> None:
        """Enqueue an event from a non-async thread (e.g. GPIO callbacks).

        This schedules :meth:`publish` on the event loop via
        ``asyncio.run_coroutine_threadsafe``.
        """
        assert self._loop is not None, "EventBus.start() has not been called"
        asyncio.run_coroutine_threadsafe(self.publish(event_type, payload), self._loop)

    # ------------------------------------------------------------------
    # Subscribe / unsubscribe
    # ------------------------------------------------------------------

    def subscribe(
        self,
        event_type: str,
        handler: Callable[..., Any],
        filter_dict: dict[str, Any] | None = None,
    ) -> str:
        """Register *handler* for *event_type*, returning a subscription id.

        If *filter_dict* is given, the handler only fires when **all**
        key/value pairs in the dict match the event payload.
        """
        sub_id = uuid.uuid4().hex
        sub = _Subscription(
            sub_id=sub_id,
            event_type=event_type,
            handler=handler,
            filter_dict=filter_dict,
        )
        self._subscriptions[sub_id] = sub
        self._type_index.setdefault(event_type, []).append(sub_id)
        return sub_id

    def unsubscribe(self, sub_id: str) -> None:
        """Remove the subscription identified by *sub_id*."""
        sub = self._subscriptions.pop(sub_id, None)
        if sub is None:
            return
        ids = self._type_index.get(sub.event_type)
        if ids:
            try:
                ids.remove(sub_id)
            except ValueError:
                pass

    # ------------------------------------------------------------------
    # Consumer loop
    # ------------------------------------------------------------------

    async def _consume(self) -> None:
        """Drain the queue and dispatch to matching handlers."""
        assert self._queue is not None
        while True:
            event = await self._queue.get()
            await self._dispatch(event)

    async def _dispatch(self, event: Event) -> None:
        sub_ids = list(self._type_index.get(event.event_type, []))
        for sub_id in sub_ids:
            sub = self._subscriptions.get(sub_id)
            if sub is None:
                continue
            if not self._matches_filter(event, sub.filter_dict):
                continue
            try:
                result = sub.handler(event)
                if asyncio.iscoroutine(result):
                    await result
            except Exception:
                _log.exception(
                    "Handler %s for '%s' raised — auto-unsubscribing",
                    sub.handler,
                    event.event_type,
                )
                self.unsubscribe(sub_id)

    @staticmethod
    def _matches_filter(event: Event, filter_dict: dict[str, Any] | None) -> bool:
        if filter_dict is None:
            return True
        return all(event.payload.get(k) == v for k, v in filter_dict.items())
