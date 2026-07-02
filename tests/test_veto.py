"""Tests for Finance's veto and its unanimous-override rule.

Covers both levels: `ParliamentProtocol._active_vetoes` directly, with
hand-built proposals (deterministic by construction, doc §15-style unit
coverage), and two full mock-driven rounds picked because they reproducibly
land on either side of the override threshold — proving the mechanism holds
end to end, not just in isolation.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

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
from symphony.models import BlackboardState, CasualtyReport, Proposal, ResourcePools, Tower, Zone
from symphony.protocol.parliament import ParliamentProtocol


def _protocol(seed: int = 1) -> ParliamentProtocol:
    provider = MockProvider(seed=seed)
    ledger = LedgerStore(Path(tempfile.mktemp(suffix=".jsonl")))
    return ParliamentProtocol(agents=[], coordinator=Coordinator(provider), ledger=ledger)


def _proposal(agent: str, *, confidence: float, action: str = "noop") -> Proposal:
    return Proposal(
        agent=agent, action=action, target_resource=None, rationale="r", confidence=confidence
    )


def _finance_veto(target: str = "helicopter") -> Proposal:
    return Proposal(
        agent="finance",
        action="flag_budget_risk",
        target_resource="budget",
        rationale="budget is tight",
        confidence=0.9,
        veto=True,
        veto_target=target,
        cost=0.0,
    )


def test_veto_holds_when_confidence_is_below_the_override_threshold() -> None:
    protocol = _protocol()
    proposals = [
        _finance_veto(),
        _proposal("logistics", confidence=0.9),
        _proposal("medical", confidence=0.9),
        _proposal("comms", confidence=0.9),
        _proposal("sar", confidence=0.5),  # below threshold -> no unanimous override
    ]

    assert protocol._active_vetoes(proposals) == {"helicopter"}


def test_veto_overridden_when_all_four_are_confident() -> None:
    protocol = _protocol()
    proposals = [
        _finance_veto(),
        _proposal("logistics", confidence=0.8),
        _proposal("medical", confidence=0.9),
        _proposal("comms", confidence=0.85),
        _proposal("sar", confidence=0.75),  # exactly at threshold still counts
    ]

    assert protocol._active_vetoes(proposals) == set()


def test_an_abstention_prevents_override_even_if_others_are_confident() -> None:
    protocol = _protocol()
    proposals = [
        _finance_veto(),
        _proposal("logistics", confidence=0.9),
        _proposal("medical", confidence=0.9),
        _proposal("comms", confidence=0.9),
        _proposal("sar", confidence=0.0, action="abstain"),
    ]

    assert protocol._active_vetoes(proposals) == {"helicopter"}


def test_no_veto_when_finance_does_not_flag_risk() -> None:
    protocol = _protocol()
    names = ("logistics", "medical", "comms", "sar")
    proposals = [_proposal(name, confidence=0.9) for name in names]

    assert protocol._active_vetoes(proposals) == set()


def _tight_budget_blackboard() -> BlackboardState:
    return BlackboardState(
        tick=4,
        zones={
            "zone-1": Zone(id="zone-1", name="Ridgeline District", lat=38.90, lng=-120.98),
            "zone-2": Zone(id="zone-2", name="Lakeview Basin", lat=38.85, lng=-121.05),
        },
        resources=ResourcePools(
            helicopters=2, medic_teams=3, sar_teams=2, comms_towers=2, budget_remaining=5_000.0
        ),
        towers={
            "tower-1": Tower(id="tower-1", zone_id="zone-1"),
            "tower-2": Tower(id="tower-2", zone_id="zone-2"),
        },
        casualties=[
            CasualtyReport(zone_id="zone-1", count=6, severity="critical", tick_reported=4)
        ],
    )


def _build_round(seed: int) -> ParliamentProtocol:
    provider = MockProvider(seed=seed)
    agents = [
        LogisticsAgent(provider),
        MedicalAgent(provider),
        CommsAgent(provider),
        FinanceAgent(provider),
        SarAgent(provider),
    ]
    coordinator = Coordinator(provider)
    ledger = LedgerStore(Path(tempfile.mktemp(suffix=".jsonl")))
    return ParliamentProtocol(agents, coordinator, ledger)


def test_full_round_drops_the_vetoed_proposal_when_not_overridden() -> None:
    # seed=1: Finance vetoes "helicopter" under a tight budget; SAR's confidence
    # (0.56) falls below the override threshold, so the veto holds.
    protocol = _build_round(seed=1)
    result = protocol.run_round(4, _tight_budget_blackboard())

    finance_proposal = next(p for p in result.proposals if p.agent == "finance")
    assert finance_proposal.veto is True
    assert finance_proposal.veto_target == "helicopter"

    committed_agents = {c["agent"] for c in result.outcome["committed"]}
    assert "medical" not in committed_agents
    assert any(v["target_resource"] == "helicopter" for v in result.outcome["vetoed"])


def test_full_round_commits_the_proposal_when_veto_is_unanimously_overridden() -> None:
    # seed=13: same tight-budget scenario, but all four non-Finance agents
    # happen to propose with confidence >= the override threshold this tick.
    protocol = _build_round(seed=13)
    result = protocol.run_round(4, _tight_budget_blackboard())

    finance_proposal = next(p for p in result.proposals if p.agent == "finance")
    assert finance_proposal.veto is True

    committed_agents = {c["agent"] for c in result.outcome["committed"]}
    assert "medical" in committed_agents
    assert result.outcome["vetoed"] == []
