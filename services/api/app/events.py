"""In-process publish/subscribe used by the Server-Sent Events endpoint.

Events carry ids and status only (never comment bodies). A single API worker is
assumed (research.md, Decision 3).
"""

from __future__ import annotations

import asyncio
import threading
from typing import Any


class Broker:
    """Fan-out of event dictionaries to asyncio subscriber queues."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._subscribers: list[tuple[asyncio.AbstractEventLoop, asyncio.Queue]] = []

    def subscribe(self) -> asyncio.Queue:
        """Register the calling coroutine's loop and return its private queue."""
        queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
        with self._lock:
            self._subscribers.append((asyncio.get_running_loop(), queue))
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        """Remove a subscriber queue."""
        with self._lock:
            self._subscribers = [s for s in self._subscribers if s[1] is not queue]

    def publish(self, event: dict[str, Any]) -> None:
        """Deliver ``event`` to every subscriber; safe to call from worker threads."""
        with self._lock:
            targets = list(self._subscribers)
        for loop, queue in targets:
            try:
                loop.call_soon_threadsafe(self._put, queue, event)
            except RuntimeError:  # loop already closed
                self.unsubscribe(queue)

    @staticmethod
    def _put(queue: asyncio.Queue, event: dict[str, Any]) -> None:
        if not queue.full():
            queue.put_nowait(event)


broker = Broker()
