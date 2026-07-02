"""Interface for publishing simulator events.

The simulator publishes every scheduled event it injects; this interface
exists so a real broker (ApsaraMQ for Kafka — added as a later-phase backend)
can be swapped in without the simulator knowing which backend is active.
Selected via `symphony.config`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from symphony.models import SimEvent


class EventBus(ABC):
    """Publishes and drains simulator events."""

    @abstractmethod
    def publish(self, event: SimEvent) -> None:
        """Publish one event."""

    @abstractmethod
    def drain(self) -> list[SimEvent]:
        """Return and clear all events published since the last drain."""
