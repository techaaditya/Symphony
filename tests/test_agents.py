"""Tests for the specialist agents, Coordinator, and BaseAgent's graceful degradation."""

from __future__ import annotations

import json

from symphony.agents import (
    CommsAgent,
    Coordinator,
    FinanceAgent,
    LogisticsAgent,
    MedicalAgent,
    SarAgent,
)
from symphony.llm.provider import LLMResult, MockProvider
from symphony.models import BlackboardState, ResourcePools, Tower, Zone


def _blackboard() -> BlackboardState:
    return BlackboardState(
        tick=4,
        zones={
            "zone-1": Zone(
                id="zone-1", name="Ridgeline District", lat=38.90, lng=-120.98, fire_intensity=0.5
            ),
            "zone-2": Zone(
                id="zone-2", name="Lakeview Basin", lat=38.85, lng=-121.05, fire_intensity=0.0
            ),
        },
        resources=ResourcePools(
            helicopters=2, medic_teams=3, sar_teams=2, comms_towers=2, budget_remaining=500_000.0
        ),
        towers={
            "tower-1": Tower(id="tower-1", zone_id="zone-1", operational=False),
            "tower-2": Tower(id="tower-2", zone_id="zone-2", operational=True),
        },
    )


class AlwaysFailsProvider:
    """A provider whose every call raises — used to test graceful degradation."""

    def __init__(self) -> None:
        self.call_count = 0

    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float = 0.2,
        max_tokens: int = 400,
    ) -> LLMResult:
        self.call_count += 1
        raise RuntimeError("simulated LLM outage")


class BadSchemaProvider:
    """A provider that always returns well-formed JSON with a disallowed action."""

    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float = 0.2,
        max_tokens: int = 400,
    ) -> LLMResult:
        request = json.loads(user_prompt)
        payload = {
            "agent": request["agent"],
            "action": "not_a_real_action",
            "target_resource": "helicopter",
            "rationale": "bad schema",
            "confidence": 0.5,
        }
        return LLMResult(text=json.dumps(payload), total_tokens=10)


AGENT_CLASSES = [LogisticsAgent, MedicalAgent, CommsAgent, FinanceAgent, SarAgent]


def test_every_specialist_produces_a_valid_proposal_via_mock() -> None:
    provider = MockProvider(seed=42)
    blackboard = _blackboard()
    for cls in AGENT_CLASSES:
        agent = cls(provider)
        proposal = agent.propose(blackboard, tick=4)
        assert proposal.agent == agent.name
        assert proposal.action == "abstain" or proposal.action in agent.allowed_actions
        assert 0.0 <= proposal.confidence <= 1.0


def test_expertise_weights_favor_specialty_over_default() -> None:
    agent = LogisticsAgent(MockProvider(seed=1))
    assert agent.vote("helicopter") == 1.0
    assert agent.vote("medic_team") == agent.default_expertise_weight  # unfamiliar resource
    assert agent.vote(None) == agent.default_expertise_weight


def test_finance_defaults_to_baseline_weight_outside_budget() -> None:
    agent = FinanceAgent(MockProvider(seed=1))
    assert agent.vote("budget") == 1.0
    assert agent.vote("helicopter") == agent.default_expertise_weight


def test_propose_abstains_after_provider_outage_without_raising() -> None:
    provider = AlwaysFailsProvider()
    agent = MedicalAgent(provider, retry_backoff_seconds=0.0)

    proposal = agent.propose(_blackboard(), tick=4, retries=3)

    assert proposal.action == "abstain"
    assert proposal.agent == "medical"
    assert proposal.confidence == 0.0
    assert provider.call_count == 3  # retried the full budget before abstaining


def test_propose_retries_and_abstains_on_schema_validation_failure() -> None:
    provider = BadSchemaProvider()
    agent = LogisticsAgent(provider, retry_backoff_seconds=0.0)

    proposal = agent.propose(_blackboard(), tick=4, retries=2)

    assert proposal.action == "abstain"


def test_rebut_degrades_to_empty_string_on_outage() -> None:
    provider = AlwaysFailsProvider()
    agent = SarAgent(provider, retry_backoff_seconds=0.0)

    rebuttal = agent.rebut(
        _blackboard(),
        tick=4,
        resource="helicopter",
        opposing_agent="medical",
        opposing_rationale="a confirmed casualty needs it",
        retries=2,
    )

    assert rebuttal == ""


def test_score_persuasiveness_degrades_to_zero_on_outage() -> None:
    provider = AlwaysFailsProvider()
    agent = MedicalAgent(provider, retry_backoff_seconds=0.0)

    score = agent.score_persuasiveness(
        _blackboard(), tick=4, rebuttal_text="a real rebuttal", retries=2
    )

    assert score == 0.0


def test_score_persuasiveness_short_circuits_on_empty_rebuttal() -> None:
    provider = AlwaysFailsProvider()
    agent = MedicalAgent(provider)

    score = agent.score_persuasiveness(_blackboard(), tick=4, rebuttal_text="")

    assert score == 0.0
    assert provider.call_count == 0  # never called the provider at all


def test_coordinator_rules_and_cites_transcript_via_mock() -> None:
    coordinator = Coordinator(MockProvider(seed=42))
    ruling = coordinator.rule(
        _blackboard(),
        tick=4,
        resource="helicopter",
        candidates=["medical", "sar"],
        votes={"medical": 1.1, "sar": 1.0},
        debate_log=[{"agent": "medical", "rebuttal": "a confirmed casualty is time-critical now"}],
    )

    assert ruling["ruling"] == "medical"
    assert "confirmed casualty is time-critical now" in ruling["rationale"]


def test_coordinator_falls_back_to_highest_vote_on_outage() -> None:
    coordinator = Coordinator(AlwaysFailsProvider(), retry_backoff_seconds=0.0)
    ruling = coordinator.rule(
        _blackboard(),
        tick=4,
        resource="helicopter",
        candidates=["medical", "sar"],
        votes={"medical": 1.1, "sar": 1.4},
        debate_log=[],
        retries=2,
    )

    assert ruling["ruling"] == "sar"
