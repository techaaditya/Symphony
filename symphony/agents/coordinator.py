"""The Coordinator: top reasoning-tier ruling authority for genuine deadlocks.

Only invoked by the Parliament Protocol (a later phase) when a weighted vote
fails to produce a majority. Its ruling must cite a specific claim from the
debate transcript (doc §3) — a ruling that could have been written without
reading the transcript is not acceptable.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from symphony.agents.base_agent import build_llm_request
from symphony.agents.prompts import COORDINATOR_SYSTEM_PROMPT
from symphony.llm.provider import LLMProvider
from symphony.models import BlackboardState

logger = logging.getLogger(__name__)


class Coordinator:
    """Issues a transcript-grounded ruling on an escalated conflict."""

    name = "coordinator"
    system_prompt = COORDINATOR_SYSTEM_PROMPT

    def __init__(self, provider: LLMProvider, *, retry_backoff_seconds: float = 1.0) -> None:
        self.provider = provider
        self.retry_backoff_seconds = retry_backoff_seconds

    def rule(
        self,
        blackboard_state: BlackboardState,
        tick: int,
        *,
        resource: str,
        candidates: list[str],
        votes: dict[str, float],
        debate_log: list[dict[str, Any]],
        retries: int = 3,
    ) -> dict[str, str]:
        """Return `{"ruling": <agent name>, "rationale": <transcript-grounded text>}`.

        Falls back to the highest-voted candidate with a generic rationale if
        every LLM attempt fails — a tick must still resolve even if the
        Coordinator's own model call is unavailable (doc §7's principle,
        extended to the escalation path).
        """
        context = {
            "resource": resource,
            "candidates": candidates,
            "votes": votes,
            "debate_log": debate_log,
        }
        request = build_llm_request("coordinator_rule", self.name, tick, blackboard_state, context)
        last_error: Exception | None = None
        for attempt in range(retries):
            try:
                result = self.provider.complete(self.system_prompt, request)
                payload = json.loads(result.text)
                return {"ruling": str(payload["ruling"]), "rationale": str(payload["rationale"])}
            except Exception as exc:  # noqa: BLE001 - degrade gracefully rather than crash the tick
                last_error = exc
                logger.warning(
                    "Coordinator ruling failed (attempt %d/%d): %s", attempt + 1, retries, exc
                )
                if attempt < retries - 1:
                    time.sleep(self.retry_backoff_seconds * (2**attempt))
        logger.error("Coordinator ruling unavailable after %d attempts: %s", retries, last_error)
        fallback_winner = max(candidates, key=lambda c: votes.get(c, 0.0))
        return {
            "ruling": fallback_winner,
            "rationale": (
                "Coordinator LLM unavailable this round; fell back to the "
                "highest-scoring candidate from the weighted vote."
            ),
        }
