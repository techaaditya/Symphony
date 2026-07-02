"""Tests for the seeded disaster simulator: event injection and determinism."""

from __future__ import annotations

from symphony.models import BlackboardState
from symphony.simulator.engine import load_scenario


def test_run_advances_through_every_tick() -> None:
    sim = load_scenario("wildfire_v3", seed=1)
    history = sim.run()

    assert len(history) == sim.ticks_total
    assert [state.tick for state in history] == list(range(1, sim.ticks_total + 1))


def test_fire_spread_events_increase_zone_intensity() -> None:
    sim = load_scenario("wildfire_v3", seed=1)
    initial_intensity = sim.state.zones["zone-1"].fire_intensity
    history = sim.run()

    assert initial_intensity == 0.0
    final_zone = history[-1].zones["zone-1"]
    assert final_zone.fire_intensity > 0.0
    assert final_zone.fire_intensity <= 1.0


def test_road_closure_event_updates_road_status() -> None:
    sim = load_scenario("wildfire_v3", seed=1)
    history = sim.run()

    # scenario schedules a road_closure on zone-1 at tick 3 and zone-2 at tick 13
    assert history[2].zones["zone-1"].road_status == "closed"
    assert history[12].zones["zone-2"].road_status == "closed"


def test_casualty_and_trapped_reports_accumulate() -> None:
    sim = load_scenario("wildfire_v3", seed=1)
    history = sim.run()

    final_state = history[-1]
    assert len(final_state.casualties) == 6  # six casualty_report events in the scenario
    assert len(final_state.trapped) == 3  # three trapped_report events in the scenario
    assert all(report.zone_id in final_state.zones for report in final_state.casualties)
    assert all(report.zone_id in final_state.zones for report in final_state.trapped)


def test_tower_outage_event_marks_tower_non_operational() -> None:
    sim = load_scenario("wildfire_v3", seed=1)
    history = sim.run()

    # scenario schedules tower-1 outage at tick 5 and tower-2 outage at tick 11
    assert history[4].towers["tower-1"].operational is False
    assert history[10].towers["tower-2"].operational is False
    # the other tower should still be operational at that point
    assert history[4].towers["tower-2"].operational is True


def test_blackboard_store_reflects_latest_state() -> None:
    sim = load_scenario("wildfire_v3", seed=1)
    sim.run()

    saved = sim.blackboard_store.load()
    assert isinstance(saved, BlackboardState)
    assert saved.tick == sim.ticks_total


def test_round_runner_is_called_once_per_tick_with_live_state() -> None:
    sim = load_scenario("wildfire_v3", seed=1)
    calls: list[int] = []

    def runner(tick: int, state: BlackboardState) -> None:
        calls.append(tick)
        assert state.tick == tick

    sim.run(runner)
    assert calls == list(range(1, sim.ticks_total + 1))


def test_same_seed_produces_identical_history() -> None:
    history_a = load_scenario("wildfire_v3", seed=7).run()
    history_b = load_scenario("wildfire_v3", seed=7).run()

    assert history_a == history_b


def test_different_seeds_produce_different_magnitudes() -> None:
    history_a = load_scenario("wildfire_v3", seed=1).run()
    history_b = load_scenario("wildfire_v3", seed=2).run()

    intensities_a = [s.zones["zone-1"].fire_intensity for s in history_a]
    intensities_b = [s.zones["zone-1"].fire_intensity for s in history_b]
    assert intensities_a != intensities_b
