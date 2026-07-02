"""Interface for persisting the blackboard world-state snapshot.

The simulator and Parliament Protocol read/write a single live `BlackboardState`
in-process; this interface exists so that state can also be persisted to a real
store (Alibaba Tablestore — added as a later-phase backend) without either
caller knowing which backend is active. Selected via `symphony.config`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from symphony.models import BlackboardState


class BlackboardStore(ABC):
    """Reads and writes the current world-state snapshot."""

    @abstractmethod
    def load(self) -> BlackboardState | None:
        """Return the most recently saved state, or None if nothing has been saved yet."""

    @abstractmethod
    def save(self, state: BlackboardState) -> None:
        """Persist `state` as the current snapshot."""
