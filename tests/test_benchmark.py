"""Tests for the benchmark harness: both run modes produce well-shaped
outcomes, `run_benchmark`'s mean/SD aggregation is correct, and
`compute_outcome`'s objectives/waste definitions are exercised directly
against a hand-built blackboard state.
"""

from __future__ import annotations

import pytest

from symphony.benchmark.metrics import compute_outcome
from symphony.benchmark.run_benchmark import compare_modes, run_benchmark, run_symphony_society
from symphony.benchmark.single_agent_baseline import run_single_agent_baseline
from symphony.models import (
    BlackboardState,
    CasualtyReport,
    ResourcePools,
    Tower,
    TrappedReport,
    Zone,
)
from symphony.simulator.engine import load_scenario

_METRIC_KEYS = ("objectives_met_pct", "time_to_allocate_s", "resource_waste_pct", "token_cost")


def test_compute_outcome_computes_objectives_and_waste_directly() -> None:
    state = BlackboardState(
        tick=1,
        zones={"zone-1": Zone(id="zone-1", name="Z", lat=0.0, lng=0.0)},
        resources=ResourcePools(
            helicopters=1, medic_teams=1, sar_teams=1, comms_towers=1, budget_remaining=0.0
        ),
        towers={"tower-1": Tower(id="tower-1", zone_id="zone-1", operational=True)},
        casualties=[
            CasualtyReport(
                zone_id="zone-1", count=1, severity="minor", tick_reported=1, treated=True
            ),
            CasualtyReport(
                zone_id="zone-1", count=1, severity="critical", tick_reported=1, treated=False
            ),
        ],
        trapped=[
            TrappedReport(
                zone_id="zone-1", count=1, tick_reported=1, window_ends_tick=5, rescued=True
            )
        ],
    )

    outcome = compute_outcome(
        state, served_flags=[True, False, None, True], token_cost=100, elapsed_s=1.5
    )

    # 2 casualties (1 treated) + 1 trapped (rescued) + 1 tower (operational) = 4 objectives, 3 met.
    assert outcome["objectives_met_pct"] == round(100 * 3 / 4, 2)
    # judged flags = [True, False, True] (the None is excluded) -> 1/3 wasted.
    assert outcome["resource_waste_pct"] == round(100 * 1 / 3, 2)
    assert outcome["time_to_allocate_s"] == 1.5
    assert outcome["token_cost"] == 100


def test_compute_outcome_with_no_objectives_reports_full_credit() -> None:
    state = BlackboardState(
        tick=1,
        zones={"zone-1": Zone(id="zone-1", name="Z", lat=0.0, lng=0.0)},
        resources=ResourcePools(
            helicopters=1, medic_teams=1, sar_teams=1, comms_towers=1, budget_remaining=0.0
        ),
        towers={},
    )

    outcome = compute_outcome(state, served_flags=[], token_cost=0, elapsed_s=0.0)

    assert outcome["objectives_met_pct"] == 100.0
    assert outcome["resource_waste_pct"] == 0.0


def test_single_agent_baseline_runs_and_returns_well_shaped_metrics() -> None:
    sim = load_scenario("wildfire_v3", seed=1)
    outcome = run_single_agent_baseline(sim)

    assert set(outcome) == set(_METRIC_KEYS)
    assert 0.0 <= outcome["objectives_met_pct"] <= 100.0
    assert 0.0 <= outcome["resource_waste_pct"] <= 100.0
    assert outcome["token_cost"] > 0
    assert outcome["time_to_allocate_s"] >= 0.0


def test_symphony_society_runs_and_returns_well_shaped_metrics() -> None:
    sim = load_scenario("wildfire_v3", seed=1)
    outcome = run_symphony_society(sim)

    assert set(outcome) == set(_METRIC_KEYS)
    assert 0.0 <= outcome["objectives_met_pct"] <= 100.0
    assert 0.0 <= outcome["resource_waste_pct"] <= 100.0
    assert outcome["token_cost"] > 0
    assert outcome["time_to_allocate_s"] >= 0.0


def test_symphony_society_spends_more_tokens_than_a_single_generalist_call() -> None:
    # Five specialists proposing every tick, plus debate/vote/coordinator
    # overhead on conflicts, should cost meaningfully more tokens than one
    # generalist call per tick -- the honest cost side of the tradeoff.
    sim_society = load_scenario("wildfire_v3", seed=1)
    sim_baseline = load_scenario("wildfire_v3", seed=1)

    society = run_symphony_society(sim_society)
    baseline = run_single_agent_baseline(sim_baseline)

    assert society["token_cost"] > baseline["token_cost"]


def test_run_benchmark_aggregates_mean_and_sd_across_trials() -> None:
    result = run_benchmark("wildfire_v3", seed=1, n_trials=3, mode="single_agent")

    assert result["mode"] == "single_agent"
    assert result["n_trials"] == 3
    for key in _METRIC_KEYS:
        assert "mean" in result[key]
        assert "sd" in result[key]


def test_run_benchmark_rejects_unknown_mode() -> None:
    with pytest.raises(ValueError, match="Unknown benchmark mode"):
        run_benchmark("wildfire_v3", seed=1, n_trials=1, mode="not_a_real_mode")


def test_run_benchmark_single_trial_has_zero_sd() -> None:
    result = run_benchmark("wildfire_v3", seed=1, n_trials=1, mode="single_agent")

    for key in _METRIC_KEYS:
        assert result[key]["sd"] == 0.0


def test_compare_modes_runs_both_and_shares_the_scenario() -> None:
    comparison = compare_modes("wildfire_v3", seed=1, n_trials=2)

    assert set(comparison) == {"single_agent", "society"}
    assert comparison["single_agent"]["n_trials"] == 2
    assert comparison["society"]["n_trials"] == 2
