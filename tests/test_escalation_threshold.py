"""Doc §15's escalation-threshold test: a synthetic near-tied vote must
escalate to the Coordinator rather than either side winning by default.

Exercises `ParliamentProtocol._decide_winners` directly with a hand-built vote
tally — the doc §9 escalation logic kept exactly as specified, extracted into
its own method precisely so it's unit-testable without a full LLM-driven round.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from symphony.agents import Coordinator
from symphony.ledger.store import LedgerStore
from symphony.llm.provider import MockProvider
from symphony.protocol.parliament import ParliamentProtocol


def _protocol() -> ParliamentProtocol:
    provider = MockProvider(seed=1)
    ledger = LedgerStore(Path(tempfile.mktemp(suffix=".jsonl")))
    return ParliamentProtocol(agents=[], coordinator=Coordinator(provider), ledger=ledger)


def test_near_tied_vote_escalates_rather_than_winning_by_default() -> None:
    protocol = _protocol()
    # sar's score (1.05) does not exceed medical's (1.0) * MAJORITY_THRESHOLD (1.2 -> 1.2).
    votes = {"helicopter": {"medical": 1.0, "sar": 1.05}}

    winners, needs_escalation = protocol._decide_winners(votes)

    assert winners == {}
    assert needs_escalation == ["helicopter"]


def test_vote_exactly_at_threshold_still_escalates() -> None:
    protocol = _protocol()
    # sides[0] must strictly exceed sides[1] * MAJORITY_THRESHOLD; equality escalates.
    votes = {"helicopter": {"medical": 1.2, "sar": 1.0}}

    winners, needs_escalation = protocol._decide_winners(votes)

    assert winners == {}
    assert needs_escalation == ["helicopter"]


def test_clear_margin_wins_without_escalation() -> None:
    protocol = _protocol()
    votes = {"helicopter": {"medical": 1.5, "sar": 1.0}}  # 1.5 > 1.0 * 1.2

    winners, needs_escalation = protocol._decide_winners(votes)

    assert winners == {"helicopter": "medical"}
    assert needs_escalation == []


def test_single_sided_conflict_wins_without_escalation() -> None:
    protocol = _protocol()
    votes = {"helicopter": {"medical": 0.7}}

    winners, needs_escalation = protocol._decide_winners(votes)

    assert winners == {"helicopter": "medical"}
    assert needs_escalation == []


def test_multiple_conflicts_are_decided_independently() -> None:
    protocol = _protocol()
    votes = {
        "helicopter": {"medical": 1.0, "sar": 1.05},  # near-tied -> escalate
        "comms_tower": {"comms": 2.0, "logistics": 0.5},  # clear win
    }

    winners, needs_escalation = protocol._decide_winners(votes)

    assert winners == {"comms_tower": "comms"}
    assert needs_escalation == ["helicopter"]
