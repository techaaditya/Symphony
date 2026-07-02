"""Doc §15's abstention-path test: force one agent's proposal to fail and
confirm the round completes with that agent abstaining, rather than crashing."""

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
from symphony.llm.provider import LLMResult, MockProvider
from symphony.models import BlackboardState, ResourcePools, Tower, Zone
from symphony.protocol.parliament import ParliamentProtocol


class AlwaysFailsProvider:
    """Every call raises — simulates a total LLM outage for one agent."""

    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float = 0.2,
        max_tokens: int = 400,
    ) -> LLMResult:
        raise RuntimeError("simulated LLM outage")


def _blackboard() -> BlackboardState:
    return BlackboardState(
        tick=1,
        zones={"zone-1": Zone(id="zone-1", name="Ridgeline District", lat=38.90, lng=-120.98)},
        resources=ResourcePools(
            helicopters=2, medic_teams=3, sar_teams=2, comms_towers=2, budget_remaining=500_000.0
        ),
        towers={"tower-1": Tower(id="tower-1", zone_id="zone-1")},
    )


def test_round_completes_when_one_agent_abstains() -> None:
    healthy_provider = MockProvider(seed=42)
    failing_provider = AlwaysFailsProvider()

    agents = [
        LogisticsAgent(healthy_provider),
        MedicalAgent(healthy_provider),
        CommsAgent(failing_provider, retry_backoff_seconds=0.0),  # this one is down
        FinanceAgent(healthy_provider),
        SarAgent(healthy_provider),
    ]
    coordinator = Coordinator(healthy_provider)
    ledger = LedgerStore(Path(tempfile.mktemp(suffix=".jsonl")))
    protocol = ParliamentProtocol(agents, coordinator, ledger)

    result = protocol.run_round(1, _blackboard())

    comms_proposal = next(p for p in result.proposals if p.agent == "comms")
    assert comms_proposal.action == "abstain"
    assert comms_proposal.confidence == 0.0
    # The round still produced one proposal per agent and reached a commit outcome.
    assert len(result.proposals) == 5
    assert "committed" in result.outcome


def test_abstained_agent_is_excluded_from_conflict_detection() -> None:
    healthy_provider = MockProvider(seed=42)
    failing_provider = AlwaysFailsProvider()

    # Even the agent most likely to compete for "helicopter" abstains here;
    # it must not appear in any conflict or commit.
    agents = [
        LogisticsAgent(healthy_provider),
        MedicalAgent(failing_provider, retry_backoff_seconds=0.0),
        CommsAgent(healthy_provider),
        FinanceAgent(healthy_provider),
        SarAgent(healthy_provider),
    ]
    coordinator = Coordinator(healthy_provider)
    ledger = LedgerStore(Path(tempfile.mktemp(suffix=".jsonl")))
    protocol = ParliamentProtocol(agents, coordinator, ledger)

    result = protocol.run_round(1, _blackboard())

    for proposals in result.conflicts.values():
        assert all(p.agent != "medical" for p in proposals)
    assert all(c["agent"] != "medical" for c in result.outcome["committed"])
