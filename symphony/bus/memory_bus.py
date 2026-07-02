"""In-memory event bus — the zero-config default backend."""

from __future__ import annotations

from symphony.bus.base import EventBus
from symphony.models import SimEvent


class InMemoryEventBus(EventBus):
    """Buffers published events in a process-local list."""

    def __init__(self) -> None:
        self._queue: list[SimEvent] = []

    def publish(self, event: SimEvent) -> None:
        self._queue.append(event)

    def drain(self) -> list[SimEvent]:
        events, self._queue = self._queue, []
        return events
