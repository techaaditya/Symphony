"""The single-agent baseline (doc §10): one generalist decision-maker, no
Parliament Protocol, benchmarked against the five-agent society on identical
scenarios and seeds.

Design decision the doc names but doesn't specify beyond "one generalist
agent" (same pattern as the vote formula and veto override in
`protocol/parliament.py` — a concrete rule beats an implicit one): the
generalist sees the exact same blackboard the society sees and calls the
exact same pluggable `LLMProvider`, but gets exactly **one**
`generalist_decide` completion per tick instead of five parallel proposals.
That is the real, honest bottleneck a lone decision-maker faces — not a
deliberately weakened model or a handicapped prompt. Its chosen action is
committed through `symphony.protocol.commit`, the same module the Parliament
Protocol commits through, so "what committing a proposal means" — pool
decrement, budget spend, casualty/trapped/tower bookkeeping — is identical
between modes. Only how a proposal gets chosen differs.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict
from typing import TYPE_CHECKING, Any

from symphony.benchmark.metrics import compute_outcome
from symphony.benchmark.token_counter import TokenCountingProvider
from symphony.llm.provider import LLMProvider, get_provider
from symphony.models import BlackboardState, Proposal
from symphony.protocol.commit import apply_commit

if TYPE_CHECKING:
    from symphony.simulator.engine import Simulator

_SYSTEM_PROMPT = (
    "You are a single generalist crisis-response coordinator with no specialist "
    "team to delegate to. Each tick you see the full blackboard state and must "
    "choose exactly ONE action across medical, search & rescue, comms, and "
    "logistics needs, prioritized by urgency — you cannot act on more than one "
    "need this tick. Respond ONLY in JSON: "
    '{"domain": "medical"|"sar"|"comms"|"logistics"|null, "action": "<action>", '
    '"target_resource": "<resource type>"|null, "rationale": "<why>", '
    '"confidence": <0-1 float>, "cost": <float>}'
)


class SingleAgentBaseline:
    """Asks the provider for one decision per tick and commits it directly."""

    def __init__(self, provider: LLMProvider) -> None:
        self._counting_provider = TokenCountingProvider(provider)

    @property
    def total_tokens(self) -> int:
        return self._counting_provider.total_tokens

    def decide_and_commit(self, tick: int, blackboard_state: BlackboardState) -> dict[str, Any]:
        """Ask for this tick's single decision and commit it to the blackboard."""
        request = json.dumps(
            {
                "call_type": "generalist_decide",
                "agent": "generalist",
                "tick": tick,
                "blackboard": asdict(blackboard_state),
                "context": {},
            },
            default=str,
        )
        result = self._counting_provider.complete(_SYSTEM_PROMPT, request)
        payload = json.loads(result.text)

        proposal = Proposal(
            agent=payload.get("domain") or "generalist",
            action=payload["action"],
            target_resource=payload.get("target_resource"),
            rationale=str(payload.get("rationale", "")),
            confidence=float(payload.get("confidence", 0.0)),
            cost=float(payload.get("cost", 0.0)),
        )
        if proposal.target_resource is None:
            return {
                "agent": proposal.agent,
                "action": proposal.action,
                "target_resource": None,
                "cost": 0.0,
                "served": None,
            }
        return apply_commit(proposal, blackboard_state)


def run_single_agent_baseline(
    sim: Simulator, *, provider: LLMProvider | None = None
) -> dict[str, Any]:
    """Run one full scenario with the single-agent baseline; return its outcome
    in the same shape `run_symphony_society` returns, for a direct comparison.
    """
    baseline = SingleAgentBaseline(provider or get_provider("specialist"))
    served_flags: list[bool | None] = []

    def round_runner(tick: int, state: BlackboardState) -> None:
        outcome = baseline.decide_and_commit(tick, state)
        served_flags.append(outcome["served"])

    start = time.perf_counter()
    history = sim.run(round_runner)
    elapsed_s = time.perf_counter() - start

    return compute_outcome(history[-1], served_flags, baseline.total_tokens, elapsed_s)
