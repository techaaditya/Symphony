"""BaseAgent: turns blackboard state into proposals, rebuttals, and votes.

Every specialist agent is a thin subclass that only sets `name`,
`system_prompt`, `allowed_actions`, and `expertise_weights`; all LLM-calling
behavior lives here, including the doc §7 graceful-degradation pattern:
retry with exponential backoff, then degrade gracefully rather than crash the
tick. A response that fails schema validation (e.g. a disallowed action) is
treated the same as a provider failure — it counts as a failed attempt and is
retried, not raised straight through. `propose()` degrades to an explicit
`abstain` Proposal (the doc §7/§9 contract other code depends on);
`rebut()`/`score_persuasiveness()` degrade to a neutral no-argument/no-weight
result so a mid-debate failure can't crash a round either.
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable
from dataclasses import asdict
from typing import Any, TypeVar

from symphony.llm.provider import LLMProvider
from symphony.models import BlackboardState, Proposal

logger = logging.getLogger(__name__)

# Baseline voting weight an agent carries on a resource outside its specialty
# (doc §3's "Finance ... others=0.5", applied as a universal default so every
# agent has some voice in every conflict, per the doc §6 weighted-vote formula).
DEFAULT_EXPERTISE_WEIGHT = 0.5

T = TypeVar("T")


def build_llm_request(
    call_type: str,
    agent_name: str,
    tick: int,
    blackboard_state: BlackboardState,
    context: dict[str, Any] | None = None,
) -> str:
    """Encode one LLM call as JSON, per the MockProvider/QwenProvider contract
    documented in `symphony.llm.provider`."""
    return json.dumps(
        {
            "call_type": call_type,
            "agent": agent_name,
            "tick": tick,
            "blackboard": asdict(blackboard_state),
            "context": context or {},
        }
    )


class BaseAgent:
    """Shared LLM-calling behavior for the five specialist agents."""

    name: str
    system_prompt: str
    allowed_actions: frozenset[str]
    expertise_weights: dict[str, float] = {}
    default_expertise_weight: float = DEFAULT_EXPERTISE_WEIGHT

    def __init__(self, provider: LLMProvider, *, retry_backoff_seconds: float = 1.0) -> None:
        self.provider = provider
        self.retry_backoff_seconds = retry_backoff_seconds

    def propose(
        self, blackboard_state: BlackboardState, tick: int, *, retries: int = 3
    ) -> Proposal:
        """Ask the LLM for this agent's proposed action this tick.

        Abstains (doc §7) rather than raising if every retry — including any
        that fail schema validation — is exhausted.
        """
        proposal = self._call(
            "propose", blackboard_state, tick, parse=self._proposal_from_payload, retries=retries
        )
        if proposal is None:
            return Proposal(
                agent=self.name,
                action="abstain",
                target_resource=None,
                rationale="proposal_unavailable_this_round",
                confidence=0.0,
            )
        return proposal

    def rebut(
        self,
        blackboard_state: BlackboardState,
        tick: int,
        *,
        resource: str,
        opposing_agent: str,
        opposing_rationale: str,
        retries: int = 3,
    ) -> str:
        """Ask the LLM for this agent's rebuttal in an active conflict.

        Returns "" (a non-argument) rather than raising if every retry fails,
        so a mid-debate failure degrades gracefully instead of crashing.
        """
        context = {
            "resource": resource,
            "opposing_agent": opposing_agent,
            "opposing_rationale": opposing_rationale,
        }
        rebuttal = self._call(
            "rebut",
            blackboard_state,
            tick,
            context,
            parse=lambda payload: str(payload.get("rebuttal", "")),
            retries=retries,
        )
        return rebuttal if rebuttal is not None else ""

    def score_persuasiveness(
        self,
        blackboard_state: BlackboardState,
        tick: int,
        rebuttal_text: str,
        *,
        retries: int = 3,
    ) -> float:
        """Ask the LLM how persuasive `rebuttal_text` is, as a 0-1 score.

        An empty rebuttal (e.g. from a degraded `rebut()` call) scores 0
        without spending a call. Degrades to 0.0 — no persuasive weight — if
        every retry fails.
        """
        if not rebuttal_text:
            return 0.0
        context = {"rebuttal_text": rebuttal_text}
        score = self._call(
            "score_persuasiveness",
            blackboard_state,
            tick,
            context,
            parse=lambda payload: float(payload.get("score", 0.0)),
            retries=retries,
        )
        return score if score is not None else 0.0

    def vote(self, resource_type: str | None) -> float:
        """This agent's voting weight for `resource_type` (doc §6 weighted vote)."""
        if resource_type is None:
            return self.default_expertise_weight
        return self.expertise_weights.get(resource_type, self.default_expertise_weight)

    # -- internals --------------------------------------------------------

    def _call(
        self,
        call_type: str,
        blackboard_state: BlackboardState,
        tick: int,
        context: dict[str, Any] | None = None,
        *,
        parse: Callable[[dict[str, Any]], T],
        retries: int = 3,
    ) -> T | None:
        """Call the LLM with retry-and-backoff, applying `parse` to the decoded
        JSON payload inside the retry loop — so a parse/validation failure is
        treated the same as a provider failure and also triggers a retry.
        Returns None if every attempt failed.
        """
        request = build_llm_request(call_type, self.name, tick, blackboard_state, context)
        last_error: Exception | None = None
        for attempt in range(retries):
            try:
                result = self.provider.complete(self.system_prompt, request)
                payload = json.loads(result.text)
                return parse(payload)
            except Exception as exc:  # noqa: BLE001 - any failure degrades gracefully, per doc §7
                last_error = exc
                logger.warning(
                    "%s %s call failed (attempt %d/%d): %s",
                    self.name,
                    call_type,
                    attempt + 1,
                    retries,
                    exc,
                )
                if attempt < retries - 1:
                    time.sleep(self.retry_backoff_seconds * (2**attempt))
        logger.error(
            "%s %s call unavailable after %d attempts: %s",
            self.name,
            call_type,
            retries,
            last_error,
        )
        return None

    def _proposal_from_payload(self, payload: dict[str, Any]) -> Proposal:
        agent = payload.get("agent")
        if agent != self.name:
            raise ValueError(f"{self.name} received a proposal payload for agent {agent!r}")
        action = payload.get("action")
        if action != "abstain" and action not in self.allowed_actions:
            raise ValueError(f"{self.name} proposed disallowed action {action!r}")
        return Proposal(
            agent=agent,
            action=action,
            target_resource=payload.get("target_resource"),
            rationale=str(payload.get("rationale", "")),
            confidence=float(payload.get("confidence", 0.0)),
            veto=bool(payload.get("veto", False)),
            veto_target=payload.get("veto_target"),
            cost=float(payload.get("cost", 0.0)),
        )
