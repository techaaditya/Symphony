"""Pluggable LLM completion backend.

Every agent calls exactly one method — `LLMProvider.complete(system_prompt,
user_prompt, ...)` — regardless of which backend answers it. The default
`MockProvider` never leaves the process: it deterministically parses the
JSON-encoded `user_prompt` (see the contract below) and synthesizes a
schema-valid response using the same rules a specialist agent's system prompt
describes, so the whole Parliament Protocol — including real conflicts,
debate, and a Finance veto — can be exercised offline at zero token cost.
`QwenProvider` sends the same two strings to a live Qwen model over
DashScope's OpenAI-compatible endpoint.

## MockProvider / user_prompt contract

Agents (symphony.agents, a later phase) encode each call as a JSON object:

    {
      "call_type": "propose" | "rebut" | "score_persuasiveness" | "coordinator_rule",
      "agent": "<agent name>",
      "tick": <int>,
      "blackboard": <BlackboardState, as a plain dict>,
      "context": { ... call_type-specific fields, see below ... }
    }

- "propose": no extra context required.
- "rebut": context = {"resource": str, "opposing_agent": str, "opposing_rationale": str}
- "score_persuasiveness": context = {"rebuttal_text": str}
- "coordinator_rule": context = {"resource": str, "candidates": list[str],
  "debate_log": list[dict], "votes": dict[str, float]}

`MockProvider` returns JSON text matching the doc §3 response schemas for the
corresponding call type. `QwenProvider` relies on the live model actually
following those same schemas, per its system prompt's "Respond ONLY in JSON"
instruction.
"""

from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass
from typing import Any, Protocol

from symphony.config import SymphonyConfig, get_config
from symphony.models import SEVERITY_RANK

# Deterministic per-resource cost estimates the mock uses for proposal costing
# and Finance's veto threshold — a stand-in for what a real Qwen agent would
# reason about from the system prompt's cost-awareness instructions.
RESOURCE_COSTS: dict[str, float] = {
    "helicopter": 15_000.0,
    "medic_team": 4_000.0,
    "sar_team": 5_000.0,
    "comms_tower": 6_000.0,
    "ground_vehicle": 1_500.0,
}

# A tight time-critical window (in ticks) below which SAR prefers the faster
# helicopter over its slower dedicated ground team.
_URGENT_WINDOW_TICKS = 5


@dataclass(frozen=True)
class LLMResult:
    """The text returned by a completion call, plus its token cost."""

    text: str
    total_tokens: int


class LLMProvider(Protocol):
    """A backend that turns (system_prompt, user_prompt) into JSON-ish text."""

    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float = 0.2,
        max_tokens: int = 400,
    ) -> LLMResult: ...


class MockProvider:
    """Deterministic, offline stand-in for a real LLM.

    Given the same seed and the same (system_prompt, user_prompt), always
    returns the same output — this is what makes the determinism test and
    cheap, tokenless protocol debugging possible. The propose logic is
    intentionally written to manufacture real conflicts (Medical and SAR both
    reaching for "helicopter" under a time-critical window; Finance vetoing
    "helicopter" when the budget is tight) so the Parliament Protocol's
    debate/vote/escalate/veto paths are genuinely exercised, not dormant.
    """

    def __init__(self, seed: int = 42) -> None:
        self.seed = seed

    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float = 0.2,
        max_tokens: int = 400,
    ) -> LLMResult:
        request = json.loads(user_prompt)
        call_type = request["call_type"]
        handler = {
            "propose": self._propose,
            "rebut": self._rebut,
            "score_persuasiveness": self._score_persuasiveness,
            "coordinator_rule": self._coordinator_rule,
        }.get(call_type)
        if handler is None:
            raise ValueError(f"Unknown call_type: {call_type!r}")
        response = handler(request)
        text = json.dumps(response)
        tokens = self._estimate_tokens(system_prompt, user_prompt, text)
        return LLMResult(text=text, total_tokens=tokens)

    # -- deterministic per-call RNG --------------------------------------

    def _rng_for(self, *parts: str) -> random.Random:
        """A Random seeded from (self.seed, *parts) — reproducible, call-specific."""
        digest = hashlib.sha256(f"{self.seed}:{':'.join(parts)}".encode()).hexdigest()
        return random.Random(int(digest[:16], 16))

    def _rng_confidence(self, *parts: str, low: float = 0.55, high: float = 0.95) -> float:
        return round(self._rng_for(*parts).uniform(low, high), 2)

    def _estimate_tokens(self, system_prompt: str, user_prompt: str, response_text: str) -> int:
        # A fixed, deterministic estimate (~4 chars/token) — good enough for
        # offline cost-tracking without depending on a real tokenizer.
        chars = len(system_prompt) + len(user_prompt) + len(response_text)
        return max(1, chars // 4)

    # -- call_type dispatch -----------------------------------------------

    def _propose(self, request: dict[str, Any]) -> dict[str, Any]:
        agent = request["agent"]
        blackboard = request["blackboard"]
        tick = request["tick"]
        builder = {
            "logistics": self._propose_logistics,
            "medical": self._propose_medical,
            "comms": self._propose_comms,
            "finance": self._propose_finance,
            "sar": self._propose_sar,
        }.get(agent)
        if builder is None:
            raise ValueError(f"Unknown agent: {agent!r}")
        return builder(blackboard, tick)

    def _hottest_zone(self, blackboard: dict[str, Any]) -> dict[str, Any] | None:
        zones = list(blackboard["zones"].values())
        return max(zones, key=lambda z: z["fire_intensity"]) if zones else None

    def _untreated_casualties(self, blackboard: dict[str, Any]) -> list[dict[str, Any]]:
        return [c for c in blackboard.get("casualties", []) if not c.get("treated", False)]

    def _unrescued_trapped(self, blackboard: dict[str, Any]) -> list[dict[str, Any]]:
        return [t for t in blackboard.get("trapped", []) if not t.get("rescued", False)]

    def _propose_logistics(self, blackboard: dict[str, Any], tick: int) -> dict[str, Any]:
        zone = self._hottest_zone(blackboard)
        confidence = self._rng_confidence("logistics", "propose", str(tick))
        if zone and zone["fire_intensity"] >= 0.3:
            return {
                "agent": "logistics",
                "action": "route_helicopter",
                "target_resource": "helicopter",
                "rationale": (
                    f"Zone {zone['id']} fire intensity is {zone['fire_intensity']:.2f}; a "
                    "helicopter water drop is the fastest way to slow the spread."
                ),
                "confidence": confidence,
                "cost": RESOURCE_COSTS["helicopter"],
            }
        return {
            "agent": "logistics",
            "action": "route_ground_vehicle",
            "target_resource": "ground_vehicle",
            "rationale": (
                "No zone is currently hot enough to justify air support; ground routing suffices."
            ),
            "confidence": confidence,
            "cost": RESOURCE_COSTS["ground_vehicle"],
        }

    def _propose_medical(self, blackboard: dict[str, Any], tick: int) -> dict[str, Any]:
        confidence = self._rng_confidence("medical", "propose", str(tick))
        casualties = self._untreated_casualties(blackboard)
        if not casualties:
            return {
                "agent": "medical",
                "action": "triage_priority_change",
                "target_resource": None,
                "rationale": (
                    "No untreated casualties reported this tick; holding current triage order."
                ),
                "confidence": confidence,
                "cost": 0.0,
            }
        worst = max(casualties, key=lambda c: SEVERITY_RANK.get(c["severity"], 0))
        if worst["severity"] in ("serious", "critical"):
            return {
                "agent": "medical",
                "action": "request_helicopter_transport",
                "target_resource": "helicopter",
                "rationale": (
                    f"{worst['count']} {worst['severity']} casualties in zone {worst['zone_id']}; "
                    "a confirmed casualty's time-criticality outweighs a hypothetical future one."
                ),
                "confidence": confidence,
                "cost": RESOURCE_COSTS["helicopter"],
            }
        return {
            "agent": "medical",
            "action": "deploy_medic_team",
            "target_resource": "medic_team",
            "rationale": (
                f"{worst['count']} minor casualties in zone {worst['zone_id']}; "
                "a ground medic team is sufficient."
            ),
            "confidence": confidence,
            "cost": RESOURCE_COSTS["medic_team"],
        }

    def _propose_sar(self, blackboard: dict[str, Any], tick: int) -> dict[str, Any]:
        confidence = self._rng_confidence("sar", "propose", str(tick))
        trapped = self._unrescued_trapped(blackboard)
        if not trapped:
            return {
                "agent": "sar",
                "action": "reprioritize_search_zone",
                "target_resource": None,
                "rationale": "No unrescued trapped-persons reports outstanding this tick.",
                "confidence": confidence,
                "cost": 0.0,
            }
        most_urgent = min(trapped, key=lambda t: t["window_ends_tick"] - tick)
        window_left = most_urgent["window_ends_tick"] - tick
        if window_left <= _URGENT_WINDOW_TICKS:
            return {
                "agent": "sar",
                "action": "request_helicopter_transport",
                "target_resource": "helicopter",
                "rationale": (
                    f"{most_urgent['count']} trapped in zone {most_urgent['zone_id']} with only "
                    f"{window_left} ticks left in the rescue window; ground SAR teams are too slow."
                ),
                "confidence": confidence,
                "cost": RESOURCE_COSTS["helicopter"],
            }
        return {
            "agent": "sar",
            "action": "deploy_sar_team",
            "target_resource": "sar_team",
            "rationale": (
                f"{most_urgent['count']} trapped in zone {most_urgent['zone_id']}; "
                f"{window_left} ticks remain, a ground team can make it."
            ),
            "confidence": confidence,
            "cost": RESOURCE_COSTS["sar_team"],
        }

    def _propose_comms(self, blackboard: dict[str, Any], tick: int) -> dict[str, Any]:
        confidence = self._rng_confidence("comms", "propose", str(tick))
        down = [t for t in blackboard["towers"].values() if not t["operational"]]
        if not down:
            return {
                "agent": "comms",
                "action": "reprioritize_repair_order",
                "target_resource": None,
                "rationale": "All towers operational; no repair action needed this tick.",
                "confidence": confidence,
                "cost": 0.0,
            }
        tower = down[0]
        return {
            "agent": "comms",
            "action": "repair_tower",
            "target_resource": "comms_tower",
            "rationale": (
                f"Tower {tower['id']} is down in zone {tower['zone_id']}; other agents' "
                "coordination quality in that zone degrades every tick it stays offline."
            ),
            "confidence": confidence,
            "cost": RESOURCE_COSTS["comms_tower"],
        }

    def _propose_finance(self, blackboard: dict[str, Any], tick: int) -> dict[str, Any]:
        confidence = self._rng_confidence("finance", "propose", str(tick))
        budget = blackboard["resources"]["budget_remaining"]
        veto_threshold = RESOURCE_COSTS["helicopter"] * 3
        if budget < veto_threshold:
            return {
                "agent": "finance",
                "action": "flag_budget_risk",
                "target_resource": "budget",
                "rationale": (
                    f"Remaining budget ${budget:,.0f} is below the ${veto_threshold:,.0f} ceiling "
                    "needed to safely absorb another helicopter deployment this tick."
                ),
                "confidence": confidence,
                "veto": True,
                "veto_target": "helicopter",
                "cost": 0.0,
            }
        return {
            "agent": "finance",
            "action": "flag_budget_risk",
            "target_resource": "budget",
            "rationale": f"Remaining budget ${budget:,.0f} is healthy; no veto needed this tick.",
            "confidence": confidence,
            "cost": 0.0,
        }

    def _rebut(self, request: dict[str, Any]) -> dict[str, Any]:
        agent = request["agent"]
        context = request["context"]
        rng = self._rng_for(agent, "rebut", str(request["tick"]), context["resource"])
        text = (
            f"{agent} maintains its claim on {context['resource']}: "
            f"{context['opposing_agent']}'s rationale "
            f"('{context['opposing_rationale'][:80]}') does not outweigh the "
            "time-criticality already established this tick."
        )
        return {"agent": agent, "rebuttal": text, "confidence": round(rng.uniform(0.5, 0.9), 2)}

    def _score_persuasiveness(self, request: dict[str, Any]) -> dict[str, Any]:
        rebuttal_text = request["context"]["rebuttal_text"]
        rng = self._rng_for(request["agent"], "score", str(request["tick"]), rebuttal_text[:40])
        return {"score": round(rng.uniform(0.3, 0.9), 2)}

    def _coordinator_rule(self, request: dict[str, Any]) -> dict[str, Any]:
        context = request["context"]
        candidates: list[str] = context["candidates"]
        votes: dict[str, float] = context.get("votes", {})
        # Deterministic tie-break: highest vote score, then earliest listed.
        ranked = sorted(candidates, key=lambda c: (-votes.get(c, 0.0), candidates.index(c)))
        winner = ranked[0]
        debate_log: list[dict[str, Any]] = context.get("debate_log", [])
        cited = next((entry for entry in debate_log if entry.get("agent") == winner), None)
        cited_claim = cited["rebuttal"] if cited else "the agent's original proposal rationale"
        rationale = (
            f"After review of the debate transcript, {winner}'s position is upheld on "
            f"{context['resource']}: '{cited_claim[:120]}' was the most transcript-grounded claim."
        )
        return {"ruling": winner, "rationale": rationale}


class QwenProvider:
    """Live Qwen completion via DashScope's OpenAI-compatible endpoint.

    Imports the `openai` package lazily so `symphony.llm.provider` stays
    importable — and the mock-backed test suite runnable — without the
    optional `llm` extra installed.
    """

    def __init__(self, api_key: str, base_url: str, model: str) -> None:
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError as exc:
                raise RuntimeError(
                    "QwenProvider requires the optional 'llm' extra: pip install -e '.[llm]'"
                ) from exc
            self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        return self._client

    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float = 0.2,
        max_tokens: int = 400,
    ) -> LLMResult:
        client = self._get_client()
        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        text = response.choices[0].message.content or ""
        total_tokens = response.usage.total_tokens if response.usage else 0
        return LLMResult(text=text, total_tokens=total_tokens)


def get_provider(tier: str = "specialist", config: SymphonyConfig | None = None) -> LLMProvider:
    """Return the active LLMProvider for the given tier ('specialist' or 'coordinator').

    Selects `QwenProvider` — on the cheap tier for specialists, the top
    reasoning tier for the Coordinator — when `SYMPHONY_LLM=qwen` and a
    DashScope API key is configured; otherwise falls back to the
    deterministic, zero-cost `MockProvider`.
    """
    cfg = config or get_config()
    if cfg.llm.is_live:
        model = cfg.llm.coordinator_model if tier == "coordinator" else cfg.llm.specialist_model
        return QwenProvider(
            api_key=cfg.llm.dashscope_api_key,
            base_url=cfg.llm.dashscope_base_url,
            model=model,
        )
    return MockProvider(seed=cfg.llm.mock_seed)
