"""Happy-path tests for the Parliament Protocol: propose -> conflict -> debate
-> vote -> (escalate) -> commit, end to end against the deterministic mock."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from symphony.agents import (
    CommsAgent,
    Coordinator,
    FinanceAgent,
    LogisticsAgent,
    MedicalAgent,
    SarAgent,
)
from symphony.ledger.store import LedgerStore
from symphony.llm.provider import MockProvider
from symphony.models import (
    BlackboardState,
    CasualtyReport,
    ResourcePools,
    Tower,
    TrappedReport,
    Zone,
)
from symphony.protocol.parliament import ParliamentProtocol


def _blackboard(*, budget: float = 500_000.0) -> BlackboardState:
    return BlackboardState(
        tick=4,
        zones={
            "zone-1": Zone(id="zone-1", name="Ridgeline District", lat=38.90, lng=-120.98),
            "zone-2": Zone(id="zone-2", name="Lakeview Basin", lat=38.85, lng=-121.05),
        },
        resources=ResourcePools(
            helicopters=2, medic_teams=3, sar_teams=2, comms_towers=2, budget_remaining=budget
        ),
        towers={
            "tower-1": Tower(id="tower-1", zone_id="zone-1"),
            "tower-2": Tower(id="tower-2", zone_id="zone-2"),
        },
        # Zero fire intensity keeps Logistics off "helicopter" so the conflict
        # is a clean two-way Medical-vs-SAR contest, per the doc §18 narrative.
        casualties=[CasualtyReport(zone_id="zone-2", count=5, severity="serious", tick_reported=4)],
        trapped=[TrappedReport(zone_id="zone-2", count=3, tick_reported=4, window_ends_tick=8)],
    )


@pytest.fixture
def protocol() -> ParliamentProtocol:
    provider = MockProvider(seed=42)
    agents = [
        LogisticsAgent(provider),
        MedicalAgent(provider),
        CommsAgent(provider),
        FinanceAgent(provider),
        SarAgent(provider),
    ]
    coordinator = Coordinator(provider)
    ledger_path = Path(tempfile.mktemp(suffix=".jsonl"))
    ledger = LedgerStore(ledger_path)
    return ParliamentProtocol(agents, coordinator, ledger)


def test_round_produces_one_proposal_per_agent(protocol: ParliamentProtocol) -> None:
    result = protocol.run_round(4, _blackboard())
    expected = {"logistics", "medical", "comms", "finance", "sar"}
    assert {p.agent for p in result.proposals} == expected


def test_medical_and_sar_conflict_over_helicopter_and_resolves(
    protocol: ParliamentProtocol,
) -> None:
    result = protocol.run_round(4, _blackboard())

    assert "helicopter" in result.conflicts
    assert {p.agent for p in result.conflicts["helicopter"]} == {"medical", "sar"}

    # Bounded debate: MAX_DEBATE_ROUNDS rounds, one entry per conflicting agent per round.
    helicopter_entries = [e for e in result.debate_log if e["resource"] == "helicopter"]
    assert len(helicopter_entries) == 3 * 2  # MAX_DEBATE_ROUNDS * two conflicting agents

    assert "helicopter" in result.votes
    assert set(result.votes["helicopter"]) == {"medical", "sar"}

    # Exactly one side is committed for the contested resource — never both, never neither.
    committed_agents = {c["agent"] for c in result.outcome["committed"]}
    assert len(committed_agents & {"medical", "sar"}) == 1

    if result.escalated:
        ruling = result.outcome["coordinator_rulings"][0]
        assert ruling["resource"] == "helicopter"
        assert ruling["ruling"] in {"medical", "sar"}
        assert ruling["ruling"] in committed_agents


def test_non_conflicting_proposals_still_commit_alongside_the_resolved_conflict(
    protocol: ParliamentProtocol,
) -> None:
    result = protocol.run_round(4, _blackboard())
    committed_agents = {c["agent"] for c in result.outcome["committed"]}
    # logistics (ground_vehicle) and comms (no resource) never conflict this tick.
    assert "logistics" in committed_agents
    assert "comms" in committed_agents


def test_helicopter_pool_decrements_by_exactly_one_on_commit(protocol: ParliamentProtocol) -> None:
    blackboard = _blackboard()
    starting_helicopters = blackboard.resources.helicopters
    protocol.run_round(4, blackboard)
    assert blackboard.resources.helicopters == starting_helicopters - 1


def test_round_with_no_conflicts_commits_everything_directly(protocol: ParliamentProtocol) -> None:
    # No casualties, no trapped persons, no fire, all towers up: every agent
    # proposes a no-contest action and nothing is ever grouped into a conflict.
    blackboard = _blackboard()
    blackboard.casualties = []
    blackboard.trapped = []

    result = protocol.run_round(4, blackboard)

    assert result.conflicts == {}
    assert result.debate_log == []
    assert not result.escalated


def test_ledger_receives_one_entry_per_round(protocol: ParliamentProtocol) -> None:
    protocol.run_round(4, _blackboard())
    entries = protocol.ledger.read_all()
    assert len(entries) == 1
    assert entries[0]["tick"] == 4
