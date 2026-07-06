#!/usr/bin/env python3
"""Budget-adherence measurement: the society's Track-3 efficiency gain.

The committed benchmark (`symphony benchmark`) reports objectives met, time,
waste and token cost. This script measures the one axis that captures *why*
those objective numbers differ: whether each mode finishes the scenario within
the budget it was actually given.

The single-agent baseline has no budget governance — it approves spending tick
after tick with nothing to stop it. The five-agent society has Finance's veto,
which blocks further helicopter spend once the budget crosses a safety ceiling.
On the committed `wildfire_v3` scenario (180,000 starting budget), across the
same 20 seeds the benchmark uses, that difference is stark and reproducible:

    single-agent : ends ~-$35,000  ->  0 / 20 trials finish within budget
    society      : ends ~+$36,500  -> 20 / 20 trials finish within budget

The baseline "completes" 100% of objectives only by spending money it does not
have — an allocation the real world rejects (grounded aircraft, unpaid crews).
The society completes fewer objectives but is the only mode whose plan is
actually executable. That is the measurable efficiency gain: feasibility under
a hard resource constraint.

Zero token cost — runs on the deterministic MockProvider. Usage:

    python scripts/budget_adherence.py
    python scripts/budget_adherence.py --seed 42 --trials 20
"""

from __future__ import annotations

import argparse

from symphony.benchmark.run_benchmark import build_society
from symphony.benchmark.single_agent_baseline import SingleAgentBaseline
from symphony.llm.provider import get_provider
from symphony.simulator.engine import load_scenario


def _single_final_budget(scenario_id: str, seed: int) -> float:
    sim = load_scenario(scenario_id, seed=seed)
    baseline = SingleAgentBaseline(get_provider("specialist"))
    sim.run(lambda tick, state: baseline.decide_and_commit(tick, state))
    return sim.state.resources.budget_remaining


def _society_final_budget(scenario_id: str, seed: int) -> float:
    protocol, _, _ = build_society()
    sim = load_scenario(scenario_id, seed=seed)
    sim.run(lambda tick, state: protocol.run_round(tick, state))
    return sim.state.resources.budget_remaining


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", default="wildfire_v3")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--trials", type=int, default=20)
    args = parser.parse_args()

    seeds = [args.seed + i for i in range(args.trials)]
    single = [_single_final_budget(args.scenario, s) for s in seeds]
    society = [_society_final_budget(args.scenario, s) for s in seeds]

    single_ok = sum(1 for b in single if b >= 0)
    society_ok = sum(1 for b in society if b >= 0)

    print(f"scenario={args.scenario}  seeds={seeds[0]}..{seeds[-1]}  trials={args.trials}\n")
    print(f"{'mode':<14}{'mean final budget':>20}{'trials within budget':>24}")
    print("-" * 58)
    print(f"{'single-agent':<14}{sum(single) / len(single):>20,.0f}{single_ok:>18} / {args.trials}")
    print(f"{'society':<14}{sum(society) / len(society):>20,.0f}{society_ok:>18} / {args.trials}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
