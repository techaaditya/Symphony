"""Tests for the deterministic MockProvider and the get_provider() selector."""

from __future__ import annotations

import json

from symphony.config import LLMConfig, SymphonyConfig
from symphony.llm.provider import MockProvider, QwenProvider, get_provider

SYSTEM_PROMPT = "You are a test agent."


def _blackboard(
    *,
    fire_intensity: float = 0.0,
    casualties: list[dict] | None = None,
    trapped: list[dict] | None = None,
    towers_down: bool = False,
    budget_remaining: float = 500_000.0,
) -> dict:
    return {
        "tick": 4,
        "zones": {
            "zone-1": {"id": "zone-1", "fire_intensity": fire_intensity},
            "zone-2": {"id": "zone-2", "fire_intensity": 0.0},
        },
        "resources": {"budget_remaining": budget_remaining},
        "towers": {
            "tower-1": {"id": "tower-1", "zone_id": "zone-1", "operational": not towers_down},
            "tower-2": {"id": "tower-2", "zone_id": "zone-2", "operational": True},
        },
        "casualties": casualties or [],
        "trapped": trapped or [],
    }


def _propose_prompt(agent: str, blackboard: dict, tick: int = 4) -> str:
    request = {"call_type": "propose", "agent": agent, "tick": tick, "blackboard": blackboard}
    return json.dumps(request)


_SERIOUS_CASUALTY = [{"zone_id": "zone-1", "count": 3, "severity": "serious"}]


def test_propose_is_deterministic_for_same_seed() -> None:
    provider_a = MockProvider(seed=42)
    provider_b = MockProvider(seed=42)
    prompt = _propose_prompt("medical", _blackboard(casualties=_SERIOUS_CASUALTY))

    result_a = provider_a.complete(SYSTEM_PROMPT, prompt)
    result_b = provider_b.complete(SYSTEM_PROMPT, prompt)

    assert result_a.text == result_b.text
    assert result_a.total_tokens == result_b.total_tokens


def test_propose_differs_across_seeds() -> None:
    prompt = _propose_prompt("medical", _blackboard(casualties=_SERIOUS_CASUALTY))
    result_a = MockProvider(seed=1).complete(SYSTEM_PROMPT, prompt)
    result_b = MockProvider(seed=2).complete(SYSTEM_PROMPT, prompt)

    # Same decision (confidence is seed-derived, so text should differ).
    assert result_a.text != result_b.text


def test_propose_schema_is_valid_for_every_agent() -> None:
    provider = MockProvider(seed=42)
    blackboard = _blackboard(
        fire_intensity=0.5,
        casualties=[{"zone_id": "zone-1", "count": 2, "severity": "minor"}],
        trapped=[{"zone_id": "zone-2", "count": 1, "window_ends_tick": 20}],
        towers_down=True,
    )
    for agent in ("logistics", "medical", "comms", "finance", "sar"):
        result = provider.complete(SYSTEM_PROMPT, _propose_prompt(agent, blackboard))
        payload = json.loads(result.text)
        assert payload["agent"] == agent
        assert isinstance(payload["action"], str) and payload["action"]
        assert "target_resource" in payload
        assert isinstance(payload["rationale"], str) and payload["rationale"]
        assert 0.0 <= payload["confidence"] <= 1.0
        assert isinstance(payload["cost"], (int, float))


def test_medical_and_sar_both_reach_for_helicopter_under_time_pressure() -> None:
    """The mock is engineered to manufacture a real conflict: a serious casualty
    and a trapped-persons report with a tight window both push their agent
    toward the same scarce resource — exactly the doc §18 demo narrative."""
    provider = MockProvider(seed=42)
    # tick=4, window_ends_tick=8 -> window_left=4, within the urgent (<=5) threshold.
    blackboard = _blackboard(
        casualties=[{"zone_id": "zone-2", "count": 5, "severity": "serious"}],
        trapped=[{"zone_id": "zone-2", "count": 3, "window_ends_tick": 8}],
    )

    medical_prompt = _propose_prompt("medical", blackboard)
    sar_prompt = _propose_prompt("sar", blackboard)
    medical = json.loads(provider.complete(SYSTEM_PROMPT, medical_prompt).text)
    sar = json.loads(provider.complete(SYSTEM_PROMPT, sar_prompt).text)

    assert medical["target_resource"] == "helicopter"
    assert sar["target_resource"] == "helicopter"


def test_finance_vetoes_helicopter_when_budget_is_tight() -> None:
    provider = MockProvider(seed=42)
    tight_prompt = _propose_prompt("finance", _blackboard(budget_remaining=10_000.0))
    healthy_prompt = _propose_prompt("finance", _blackboard(budget_remaining=500_000.0))

    vetoing = json.loads(provider.complete(SYSTEM_PROMPT, tight_prompt).text)
    not_vetoing = json.loads(provider.complete(SYSTEM_PROMPT, healthy_prompt).text)

    assert vetoing["veto"] is True
    assert vetoing["veto_target"] == "helicopter"
    assert "veto" not in not_vetoing or not not_vetoing["veto"]


def test_rebut_schema_and_determinism() -> None:
    prompt = json.dumps(
        {
            "call_type": "rebut",
            "agent": "medical",
            "tick": 4,
            "blackboard": _blackboard(),
            "context": {
                "resource": "helicopter",
                "opposing_agent": "sar",
                "opposing_rationale": "trapped persons window is closing fast",
            },
        }
    )
    result_a = MockProvider(seed=42).complete(SYSTEM_PROMPT, prompt)
    result_b = MockProvider(seed=42).complete(SYSTEM_PROMPT, prompt)
    payload = json.loads(result_a.text)

    assert result_a.text == result_b.text
    assert payload["agent"] == "medical"
    assert isinstance(payload["rebuttal"], str) and payload["rebuttal"]
    assert 0.0 <= payload["confidence"] <= 1.0


def test_score_persuasiveness_schema_and_range() -> None:
    prompt = json.dumps(
        {
            "call_type": "score_persuasiveness",
            "agent": "logistics",
            "tick": 4,
            "blackboard": _blackboard(),
            "context": {"rebuttal_text": "the confirmed casualty outweighs the hypothetical one"},
        }
    )
    result = MockProvider(seed=42).complete(SYSTEM_PROMPT, prompt)
    payload = json.loads(result.text)

    assert 0.0 <= payload["score"] <= 1.0


def test_coordinator_rule_cites_debate_transcript() -> None:
    prompt = json.dumps(
        {
            "call_type": "coordinator_rule",
            "agent": "coordinator",
            "tick": 4,
            "blackboard": _blackboard(),
            "context": {
                "resource": "helicopter",
                "candidates": ["medical", "sar"],
                "votes": {"medical": 1.1, "sar": 1.0},
                "debate_log": [
                    {"agent": "medical", "rebuttal": "the confirmed casualty is time-critical now"},
                ],
            },
        }
    )
    result = MockProvider(seed=42).complete(SYSTEM_PROMPT, prompt)
    payload = json.loads(result.text)

    assert payload["ruling"] == "medical"
    assert "confirmed casualty is time-critical now" in payload["rationale"]


def test_get_provider_defaults_to_mock() -> None:
    provider = get_provider(config=SymphonyConfig())
    assert isinstance(provider, MockProvider)


def test_get_provider_requires_both_qwen_flag_and_api_key() -> None:
    # provider="qwen" but no key -> still falls back to mock.
    cfg = SymphonyConfig(llm=LLMConfig(provider="qwen", dashscope_api_key=""))
    assert isinstance(get_provider(config=cfg), MockProvider)


def test_get_provider_selects_qwen_with_tiered_models_when_live() -> None:
    cfg = SymphonyConfig(
        llm=LLMConfig(
            provider="qwen",
            dashscope_api_key="test-key",
            specialist_model="qwen-turbo",
            coordinator_model="qwen-max",
        )
    )
    specialist = get_provider(tier="specialist", config=cfg)
    coordinator = get_provider(tier="coordinator", config=cfg)

    assert isinstance(specialist, QwenProvider)
    assert isinstance(coordinator, QwenProvider)
    assert specialist.model == "qwen-turbo"
    assert coordinator.model == "qwen-max"
