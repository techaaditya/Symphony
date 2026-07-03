"""Shared commit-to-blackboard logic (doc §9's COMMIT state).

Both the Parliament Protocol and the single-agent baseline call this module so
that "committing a proposal" means exactly the same thing — the same pool
decrement, budget spend, and casualty/trapped/tower bookkeeping — regardless
of which mode decided it. That shared meaning is what makes the benchmark's
head-to-head comparison fair: the two modes differ only in *how* a proposal is
chosen, never in what happens once one is committed.
"""

from __future__ import annotations

from typing import Any

from symphony.models import SEVERITY_RANK, BlackboardState, Proposal

# Resource types backed by a decrementable pool on BlackboardState.resources.
# "ground_vehicle" and "budget" are deliberately absent: the former has no
# tracked pool, the latter is Finance's advisory target, not a claimable one.
RESOURCE_POOL_FIELD: dict[str, str] = {
    "helicopter": "helicopters",
    "medic_team": "medic_teams",
    "sar_team": "sar_teams",
    "comms_tower": "comms_towers",
}

# The only (agent, action) pairs `mark_served` can judge as having served — or
# wasted — an outstanding objective. Anything else (e.g. Logistics routing a
# helicopter to fight fire) isn't tracked for the waste metric at all: we have
# no ground-truth signal for whether it "helped", so we don't guess.
_SERVEABLE_ACTIONS: dict[str, frozenset[str]] = {
    "medical": frozenset({"request_helicopter_transport", "deploy_medic_team"}),
    "sar": frozenset({"request_helicopter_transport", "deploy_sar_team"}),
    "comms": frozenset({"repair_tower"}),
}


def apply_commit(proposal: Proposal, blackboard_state: BlackboardState) -> dict[str, Any]:
    """Deterministically apply one committed proposal to the blackboard:
    decrement the resource pool it drew from, spend its cost against the
    budget, and mark whatever casualty/trapped/tower record it served."""
    pool_field = RESOURCE_POOL_FIELD.get(proposal.target_resource or "")
    if pool_field is not None:
        current = getattr(blackboard_state.resources, pool_field)
        setattr(blackboard_state.resources, pool_field, max(0, current - 1))
    if proposal.cost:
        blackboard_state.resources.budget_remaining = round(
            blackboard_state.resources.budget_remaining - proposal.cost, 2
        )
    served = mark_served(proposal, blackboard_state)
    return {
        "agent": proposal.agent,
        "action": proposal.action,
        "target_resource": proposal.target_resource,
        "cost": proposal.cost,
        "served": served,
    }


def mark_served(proposal: Proposal, blackboard_state: BlackboardState) -> bool | None:
    """Mark the casualty/trapped/tower record this proposal addressed, if any.

    Returns `True` if an outstanding objective was actually served, `False`
    if the proposal consumed a resource for an objective that was already
    resolved by the time it committed (a wasted unit, per the benchmark's
    resource_waste_pct definition), or `None` if this (agent, action) pair
    isn't one `mark_served` tracks at all — waste is left unjudged for those.
    """
    if proposal.agent == "medical" and proposal.action in _SERVEABLE_ACTIONS["medical"]:
        untreated = [c for c in blackboard_state.casualties if not c.treated]
        if not untreated:
            return False
        worst = max(untreated, key=lambda c: SEVERITY_RANK.get(c.severity, 0))
        worst.treated = True
        return True

    if proposal.agent == "sar" and proposal.action in _SERVEABLE_ACTIONS["sar"]:
        unrescued = [t for t in blackboard_state.trapped if not t.rescued]
        if not unrescued:
            return False
        most_urgent = min(unrescued, key=lambda t: t.window_ends_tick)
        most_urgent.rescued = True
        return True

    if proposal.agent == "comms" and proposal.action in _SERVEABLE_ACTIONS["comms"]:
        down = [t for t in blackboard_state.towers.values() if not t.operational]
        if not down:
            return False
        down[0].operational = True
        return True

    return None
