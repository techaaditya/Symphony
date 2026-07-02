"""In-memory blackboard store — the zero-config default backend."""

from __future__ import annotations

from symphony.blackboard.base import BlackboardStore
from symphony.models import BlackboardState


class InMemoryBlackboardStore(BlackboardStore):
    """Holds the current world-state snapshot in a single process-local variable."""

    def __init__(self) -> None:
        self._state: BlackboardState | None = None

    def load(self) -> BlackboardState | None:
        return self._state

    def save(self, state: BlackboardState) -> None:
        self._state = state
