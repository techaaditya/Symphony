"""Core domain models shared across the simulator, agents, and Parliament Protocol.

`RoundState`, `Proposal`, and `RoundResult` are the dataclasses from the design
doc's §9 starter code, kept intact, with two intentional extensions to
`Proposal` needed for real veto enforcement in a later phase: `veto_target`
(which proposal a Finance veto blocks) and `cost` (the proposal's budget
impact, checked against the remaining budget ceiling). The rest of this module
is the typed blackboard/event schema (doc §5).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RoundState(Enum):
    """States of one Parliament Protocol round (doc §6/§9)."""

    OPEN_ROUND = "open_round"
    CONFLICT_CHECK = "conflict_check"
    DEBATE = "debate"
    VOTE = "vote"
    ESCALATE = "escalate"
    COMMIT = "commit"


@dataclass
class Proposal:
    """One agent's proposed action for the current tick."""

    agent: str
    action: str
    target_resource: str | None
    rationale: str
    confidence: float
    veto: bool = False
    # Extensions beyond the doc §9 skeleton, used by Finance veto enforcement
    # (protocol/parliament.py, a later phase) and benchmark cost accounting.
    veto_target: str | None = None
    cost: float = 0.0


@dataclass
class RoundResult:
    """The full record of one Parliament Protocol round, as written to the ledger."""

    tick: int
    proposals: list[Proposal] = field(default_factory=list)
    conflicts: dict[str, list[Proposal]] = field(default_factory=dict)
    debate_log: list[dict[str, Any]] = field(default_factory=list)
    votes: dict[str, dict[str, float]] = field(default_factory=dict)
    outcome: dict[str, Any] = field(default_factory=dict)
    escalated: bool = False


MAX_DEBATE_ROUNDS = 3
MAJORITY_THRESHOLD = 1.2  # winning side's weighted score must exceed losing side by this multiplier


# ---------------------------------------------------------------------------
# Blackboard / world-state schema (doc §5)
# ---------------------------------------------------------------------------


@dataclass
class Zone:
    """One affected geographic area."""

    id: str
    name: str
    lat: float
    lng: float
    population: int = 0
    fire_intensity: float = 0.0  # 0.0 (none) .. 1.0 (fully engulfed)
    road_status: str = "open"  # "open" | "closed"


@dataclass
class ResourcePools:
    """Scarce resources shared across all five agents.

    Resources are tracked as single global pools identified by type (e.g.
    "helicopter", not "helicopter-1"): two proposals targeting the same
    resource type conflict per the Parliament Protocol's conflict-detection
    rule, regardless of remaining pool count — matching the doc §9 skeleton.
    """

    helicopters: int
    medic_teams: int
    sar_teams: int
    comms_towers: int
    budget_remaining: float


@dataclass
class CasualtyReport:
    """A confirmed casualty event Medical must respond to."""

    zone_id: str
    count: int
    severity: str  # "minor" | "serious" | "critical"
    tick_reported: int
    treated: bool = False


@dataclass
class TrappedReport:
    """A trapped-persons event Search & Rescue must respond to within a window."""

    zone_id: str
    count: int
    tick_reported: int
    window_ends_tick: int
    rescued: bool = False


@dataclass
class Tower:
    """A comms tower Comms is responsible for keeping operational."""

    id: str
    zone_id: str
    operational: bool = True


@dataclass
class BlackboardState:
    """The full shared world-state snapshot every agent reads from."""

    tick: int
    zones: dict[str, Zone]
    resources: ResourcePools
    towers: dict[str, Tower]
    casualties: list[CasualtyReport] = field(default_factory=list)
    trapped: list[TrappedReport] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Simulator events
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SimEvent:
    """One entry in a scenario's fixed event schedule."""

    tick: int
    type: str
    zone_id: str
    payload: dict[str, Any] = field(default_factory=dict)
