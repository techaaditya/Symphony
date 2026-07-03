"""Shared outcome metrics for the benchmark harness (doc §10).

Both benchmark modes — the five-agent society and the single-agent baseline —
compute their four headline numbers (`objectives_met_pct`, `time_to_allocate_s`,
`resource_waste_pct`, `token_cost`) through this one function, so a difference
in the reported numbers reflects a real difference in how each mode allocates
resources, never a difference in how the metric was measured.

Two definitions the doc names but doesn't formalize (documented here for the
same reason `protocol/parliament.py` documents its vote formula and veto
override — a concrete, deterministic rule beats an implicit one):

- **objectives_met_pct**: of every casualty report, trapped-persons report,
  and comms tower tracked by the end of the run, the percentage that ended
  treated, rescued, or operational, respectively.
- **resource_waste_pct**: of every committed action whose outcome
  `symphony.protocol.commit.mark_served` could actually judge (i.e. it
  returned `True` or `False`, not `None`), the percentage that returned
  `False` — a resource was spent on an objective that was already resolved.
  Actions `mark_served` can't judge (e.g. Logistics routing a helicopter to
  fight fire) are excluded rather than guessed at.
"""

from __future__ import annotations

from typing import Any

from symphony.models import BlackboardState


def compute_outcome(
    final_state: BlackboardState,
    served_flags: list[bool | None],
    token_cost: int,
    elapsed_s: float,
) -> dict[str, Any]:
    """Reduce one full scenario run to the benchmark's four headline metrics."""
    objectives_total = (
        len(final_state.casualties) + len(final_state.trapped) + len(final_state.towers)
    )
    objectives_met = (
        sum(1 for c in final_state.casualties if c.treated)
        + sum(1 for t in final_state.trapped if t.rescued)
        + sum(1 for t in final_state.towers.values() if t.operational)
    )
    objectives_met_pct = 100.0 * objectives_met / objectives_total if objectives_total else 100.0

    judged = [flag for flag in served_flags if flag is not None]
    wasted = sum(1 for flag in judged if flag is False)
    resource_waste_pct = 100.0 * wasted / len(judged) if judged else 0.0

    return {
        "objectives_met_pct": round(objectives_met_pct, 2),
        "time_to_allocate_s": round(elapsed_s, 4),
        "resource_waste_pct": round(resource_waste_pct, 2),
        "token_cost": token_cost,
    }
