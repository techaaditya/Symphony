"""Doc §14's determinism check: with the mock provider and a fixed seed, a
full benchmark-mode run must be byte-identical across repeated invocations —
the property that makes cheap, tokenless protocol debugging possible before
any real Qwen call is made.
"""

from __future__ import annotations

from symphony.benchmark.run_benchmark import run_symphony_society
from symphony.benchmark.single_agent_baseline import run_single_agent_baseline
from symphony.simulator.engine import load_scenario

# time_to_allocate_s measures real wall-clock time, so it's the one field
# that's inherently non-reproducible run to run even at a fixed seed.
_DETERMINISTIC_KEYS = ("objectives_met_pct", "resource_waste_pct", "token_cost")


def _deterministic_fields(outcome: dict) -> dict:
    return {key: outcome[key] for key in _DETERMINISTIC_KEYS}


def test_single_agent_baseline_is_deterministic_for_a_fixed_seed() -> None:
    outcome_a = run_single_agent_baseline(load_scenario("wildfire_v3", seed=7))
    outcome_b = run_single_agent_baseline(load_scenario("wildfire_v3", seed=7))

    assert _deterministic_fields(outcome_a) == _deterministic_fields(outcome_b)


def test_symphony_society_is_deterministic_for_a_fixed_seed() -> None:
    outcome_a = run_symphony_society(load_scenario("wildfire_v3", seed=7))
    outcome_b = run_symphony_society(load_scenario("wildfire_v3", seed=7))

    assert _deterministic_fields(outcome_a) == _deterministic_fields(outcome_b)


def test_different_seeds_can_produce_different_society_outcomes() -> None:
    outcome_a = run_symphony_society(load_scenario("wildfire_v3", seed=1))
    outcome_b = run_symphony_society(load_scenario("wildfire_v3", seed=2))

    # Not a strict inequality on every field (token_cost is largely
    # schedule-driven, not seed-driven) -- but at least one deterministic
    # metric should differ, since seed changes jitter magnitudes and mock
    # confidences alike. time_to_allocate_s is excluded: real wall-clock
    # noise would make this assertion true for the wrong reason.
    assert _deterministic_fields(outcome_a) != _deterministic_fields(outcome_b)
