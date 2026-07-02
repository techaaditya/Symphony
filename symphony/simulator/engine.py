"""Deterministic, seeded disaster simulator.

Loads a scenario definition (a fixed event schedule over geo-located zones and
a shared resource pool), then ticks through it: each tick injects that tick's
scheduled events into the world state, publishes them to the event bus,
persists the snapshot to the blackboard store, and — if a `round_runner` is
supplied — hands the live, mutable state to it. This is where
`ParliamentProtocol.run_round` plugs in starting in a later phase; the runner
may mutate `state` directly (e.g. decrementing resource pools on commit).

Event *types*, *ticks*, and *zones* are fixed by the scenario; event
*magnitudes* (fire intensity deltas, casualty/trapped counts) are jittered by
the scenario's seeded RNG. That means the same seed always reproduces the same
world-state trace (required for the determinism test), while varying the seed
— as the benchmark harness does per trial — varies outcomes without touching
the underlying event schedule.
"""

from __future__ import annotations

import json
import random
from collections.abc import Callable
from copy import deepcopy
from pathlib import Path
from typing import Any

from symphony.blackboard.base import BlackboardStore
from symphony.blackboard.memory_store import InMemoryBlackboardStore
from symphony.bus.base import EventBus
from symphony.bus.memory_bus import InMemoryEventBus
from symphony.models import (
    BlackboardState,
    CasualtyReport,
    ResourcePools,
    SimEvent,
    Tower,
    TrappedReport,
    Zone,
)

RoundRunner = Callable[[int, BlackboardState], Any]

_JITTER_RANGE = (0.85, 1.15)
_SCENARIOS_DIR = Path(__file__).resolve().parent / "scenarios"


def load_scenario(
    scenario_id: str,
    seed: int,
    *,
    bus: EventBus | None = None,
    blackboard_store: BlackboardStore | None = None,
) -> Simulator:
    """Load a scenario JSON file by id and construct a ready-to-run `Simulator`."""
    path = _SCENARIOS_DIR / f"{scenario_id}.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    return Simulator(raw, seed, bus=bus, blackboard_store=blackboard_store)


class Simulator:
    """Ticks a fixed event schedule into a shared, mutable blackboard state."""

    def __init__(
        self,
        scenario: dict[str, Any],
        seed: int,
        *,
        bus: EventBus | None = None,
        blackboard_store: BlackboardStore | None = None,
    ) -> None:
        self.scenario_id: str = scenario["scenario_id"]
        self.ticks_total: int = scenario["ticks"]
        self.seed = seed
        self.rng = random.Random(seed)
        self.bus = bus or InMemoryEventBus()
        self.blackboard_store = blackboard_store or InMemoryBlackboardStore()

        self._events_by_tick = self._index_events(scenario["events"])
        self.state: BlackboardState = self._build_initial_state(scenario)
        self.history: list[BlackboardState] = []
        self.blackboard_store.save(deepcopy(self.state))

    def run(self, round_runner: RoundRunner | None = None) -> list[BlackboardState]:
        """Advance through every tick; return the per-tick state snapshots."""
        for tick in range(1, self.ticks_total + 1):
            for event in self._events_by_tick.get(tick, []):
                self.bus.publish(event)
                self._apply_event(event)
            self.state.tick = tick

            if round_runner is not None:
                round_runner(tick, self.state)

            self.blackboard_store.save(deepcopy(self.state))
            self.history.append(deepcopy(self.state))
        return self.history

    # -- construction ---------------------------------------------------

    def _index_events(self, raw_events: list[dict[str, Any]]) -> dict[int, list[SimEvent]]:
        by_tick: dict[int, list[SimEvent]] = {}
        for raw in raw_events:
            event = SimEvent(
                tick=raw["tick"],
                type=raw["type"],
                zone_id=raw["zone_id"],
                payload=raw.get("payload", {}),
            )
            by_tick.setdefault(event.tick, []).append(event)
        return by_tick

    def _build_initial_state(self, scenario: dict[str, Any]) -> BlackboardState:
        zones = {
            z["id"]: Zone(
                id=z["id"],
                name=z["name"],
                lat=z["lat"],
                lng=z["lng"],
                population=z.get("population", 0),
            )
            for z in scenario["zones"]
        }
        towers = {
            t["id"]: Tower(id=t["id"], zone_id=t["zone_id"]) for t in scenario.get("towers", [])
        }
        r = scenario["resources"]
        resources = ResourcePools(
            helicopters=r["helicopters"],
            medic_teams=r["medic_teams"],
            sar_teams=r["sar_teams"],
            comms_towers=r["comms_towers"],
            budget_remaining=r["budget"],
        )
        return BlackboardState(tick=0, zones=zones, resources=resources, towers=towers)

    # -- event application (deterministic given the seed) ---------------

    def _apply_event(self, event: SimEvent) -> None:
        handler = {
            "fire_spread": self._apply_fire_spread,
            "road_closure": self._apply_road_closure,
            "casualty_report": self._apply_casualty_report,
            "trapped_report": self._apply_trapped_report,
            "tower_outage": self._apply_tower_outage,
        }.get(event.type)
        if handler is None:
            raise ValueError(f"Unknown scenario event type: {event.type!r}")
        handler(event)

    def _jitter(self, value: float) -> float:
        return value * self.rng.uniform(*_JITTER_RANGE)

    def _apply_fire_spread(self, event: SimEvent) -> None:
        zone = self.state.zones[event.zone_id]
        delta = self._jitter(event.payload["intensity_delta"])
        zone.fire_intensity = round(min(1.0, zone.fire_intensity + delta), 3)

    def _apply_road_closure(self, event: SimEvent) -> None:
        self.state.zones[event.zone_id].road_status = "closed"

    def _apply_casualty_report(self, event: SimEvent) -> None:
        count = max(1, round(self._jitter(event.payload["count"])))
        self.state.casualties.append(
            CasualtyReport(
                zone_id=event.zone_id,
                count=count,
                severity=event.payload["severity"],
                tick_reported=event.tick,
            )
        )

    def _apply_trapped_report(self, event: SimEvent) -> None:
        count = max(1, round(self._jitter(event.payload["count"])))
        self.state.trapped.append(
            TrappedReport(
                zone_id=event.zone_id,
                count=count,
                tick_reported=event.tick,
                window_ends_tick=event.payload["window_ends_tick"],
            )
        )

    def _apply_tower_outage(self, event: SimEvent) -> None:
        tower_id = event.payload.get("tower_id")
        if tower_id is None:
            tower_id = next(t.id for t in self.state.towers.values() if t.zone_id == event.zone_id)
        self.state.towers[tower_id].operational = False
