"""The Parliament Protocol state machine (doc §6/§9): propose -> conflict-check
-> debate -> vote -> escalate -> commit.

The doc §9 skeleton's state machine, retry/abstain handling, and escalation
threshold are kept exactly as specified — bugs there would silently corrupt
the benchmark's numbers. This module fills in every stub the doc left as
`NotImplementedError`, plus one mechanism the doc describes but doesn't give
starter code for: the Finance veto.

Two design decisions this project had to make, since the FINAL doc references
them without giving a concrete formula:

- **Weighted vote** (`_run_weighted_vote`): for a conflict on resource `R` of
  type `T`, each side `s` (a conflicting agent) scores

      side_score(s) = sum over every agent `voter` in the society of
          voter.vote(T) * average_persuasiveness(voter's score of s's rebuttal)

  averaged across every bounded debate round. Every agent gets a say, not just
  the two in conflict, weighted by how much that voter actually knows about
  resource type `T` (`BaseAgent.vote`, doc §6).

- **Finance veto override** (`_active_vetoes`): the doc specifies the veto is
  "overridable only by unanimous vote of the other four agents" but doesn't
  define the override mechanism. We interpret it deterministically, in
  keeping with "agents propose, deterministic code adjudicates": an override
  succeeds only if all four non-Finance agents proposed (none abstained) with
  confidence at or above `OVERRIDE_CONFIDENCE_THRESHOLD` this tick — unanimous
  conviction strong enough to accept the budget risk Finance flagged, read
  directly off proposals the agents already made, with no extra LLM call.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from symphony.models import (
    MAJORITY_THRESHOLD,
    MAX_DEBATE_ROUNDS,
    SEVERITY_RANK,
    BlackboardState,
    Proposal,
    RoundResult,
)

if TYPE_CHECKING:
    from symphony.agents.base_agent import BaseAgent
    from symphony.agents.coordinator import Coordinator
    from symphony.ledger.store import LedgerStore

logger = logging.getLogger(__name__)

# Resource types backed by a decrementable pool on BlackboardState.resources.
# "ground_vehicle" and "budget" are deliberately absent: the former has no
# tracked pool, the latter is Finance's advisory target, not a claimable one.
_RESOURCE_POOL_FIELD: dict[str, str] = {
    "helicopter": "helicopters",
    "medic_team": "medic_teams",
    "sar_team": "sar_teams",
    "comms_tower": "comms_towers",
}

_NON_FINANCE_AGENTS = frozenset({"logistics", "medical", "comms", "sar"})
OVERRIDE_CONFIDENCE_THRESHOLD = 0.75


class ParliamentProtocol:
    """Runs one Parliament round per tick over a fixed set of agents."""

    def __init__(
        self, agents: list[BaseAgent], coordinator: Coordinator, ledger: LedgerStore
    ) -> None:
        self.agents = agents
        self.coordinator = coordinator
        self.ledger = ledger

    def run_round(self, tick: int, blackboard_state: BlackboardState) -> RoundResult:
        result = RoundResult(tick=tick)

        # STATE: OPEN_ROUND. BaseAgent.propose() already retries-then-abstains
        # internally (doc §7), so no separate `_safe_propose` wrapper is needed.
        for agent in self.agents:
            result.proposals.append(agent.propose(blackboard_state, tick))

        # STATE: CONFLICT_CHECK
        conflicts = self._detect_conflicts(result.proposals)
        result.conflicts = conflicts
        if not conflicts:
            result.outcome = self._commit_all(result.proposals, blackboard_state)
            self.ledger.write(result)
            return result

        # STATE: DEBATE (bounded)
        for round_num in range(1, MAX_DEBATE_ROUNDS + 1):
            for resource, conflicting_proposals in conflicts.items():
                entries = self._run_debate_round(
                    resource, conflicting_proposals, blackboard_state, tick, round_num
                )
                result.debate_log.extend(entries)

        # STATE: VOTE
        votes = self._run_weighted_vote(conflicts, result.debate_log)
        result.votes = votes
        winners, needs_escalation = self._decide_winners(votes)

        # STATE: ESCALATE (only for undecided conflicts)
        for resource in needs_escalation:
            candidates = [p.agent for p in conflicts[resource]]
            resource_debate = [e for e in result.debate_log if e["resource"] == resource]
            ruling = self.coordinator.rule(
                blackboard_state,
                tick,
                resource=resource,
                candidates=candidates,
                votes=votes[resource],
                debate_log=resource_debate,
            )
            winners[resource] = ruling["ruling"]
            result.escalated = True
            rulings = result.outcome.setdefault("coordinator_rulings", [])
            rulings.append({"resource": resource, **ruling})

        # STATE: COMMIT
        result.outcome.update(self._commit_winners(winners, result.proposals, blackboard_state))
        self.ledger.write(result)
        return result

    # -- CONFLICT_CHECK -----------------------------------------------------

    def _detect_conflicts(self, proposals: list[Proposal]) -> dict[str, list[Proposal]]:
        by_resource: dict[str, list[Proposal]] = {}
        for p in proposals:
            if p.action == "abstain" or p.target_resource is None:
                continue
            by_resource.setdefault(p.target_resource, []).append(p)
        return {res: props for res, props in by_resource.items() if len(props) > 1}

    # -- DEBATE ---------------------------------------------------------

    def _run_debate_round(
        self,
        resource: str,
        conflicting_proposals: list[Proposal],
        blackboard_state: BlackboardState,
        tick: int,
        round_num: int,
    ) -> list[dict[str, Any]]:
        """One bounded debate round for a single conflict: each conflicting
        agent rebuts its strongest opponent, then every agent NOT party to
        this conflict scores that rebuttal's persuasiveness."""
        agents_by_name = {a.name: a for a in self.agents}
        conflicting_names = {p.agent for p in conflicting_proposals}
        neutral_agents = [a for a in self.agents if a.name not in conflicting_names]

        entries: list[dict[str, Any]] = []
        for proposal in conflicting_proposals:
            agent = agents_by_name[proposal.agent]
            opposing = max(
                (p for p in conflicting_proposals if p.agent != proposal.agent),
                key=lambda p: p.confidence,
            )
            rebuttal_text = agent.rebut(
                blackboard_state,
                tick,
                resource=resource,
                opposing_agent=opposing.agent,
                opposing_rationale=opposing.rationale,
            )
            scores = {
                scorer.name: scorer.score_persuasiveness(blackboard_state, tick, rebuttal_text)
                for scorer in neutral_agents
            }
            entries.append(
                {
                    "resource": resource,
                    "round": round_num,
                    "agent": proposal.agent,
                    "rebuttal": rebuttal_text,
                    "scores": scores,
                }
            )
        return entries

    # -- VOTE -------------------------------------------------------------

    def _run_weighted_vote(
        self,
        conflicts: dict[str, list[Proposal]],
        debate_log: list[dict[str, Any]],
    ) -> dict[str, dict[str, float]]:
        """Expertise-weighted vote tally — see the module docstring for the formula."""
        agents_by_name = {a.name: a for a in self.agents}
        votes: dict[str, dict[str, float]] = {}
        for resource, proposals in conflicts.items():
            resource_entries = [e for e in debate_log if e["resource"] == resource]
            tally: dict[str, float] = {}
            for proposal in proposals:
                side = proposal.agent
                side_entries = [e for e in resource_entries if e["agent"] == side]
                if not side_entries:
                    tally[side] = 0.0
                    continue
                side_score = 0.0
                for voter_name in side_entries[0]["scores"]:
                    voter = agents_by_name.get(voter_name)
                    if voter is None:
                        continue
                    voter_scores = [e["scores"].get(voter_name, 0.0) for e in side_entries]
                    avg_persuasiveness = sum(voter_scores) / len(voter_scores)
                    side_score += voter.vote(resource) * avg_persuasiveness
                tally[side] = round(side_score, 4)
            votes[resource] = tally
        return votes

    def _decide_winners(
        self, votes: dict[str, dict[str, float]]
    ) -> tuple[dict[str, str], list[str]]:
        """For each conflict's vote tally, decide a clear winner or flag it for
        escalation per MAJORITY_THRESHOLD (doc §9's exact escalation logic,
        extracted into its own method so it's directly unit-testable without a
        full LLM-driven round — doc §15's escalation-threshold test)."""
        winners: dict[str, str] = {}
        needs_escalation: list[str] = []
        for resource, tally in votes.items():
            sides = sorted(tally.items(), key=lambda kv: -kv[1])
            if len(sides) < 2 or sides[0][1] > sides[1][1] * MAJORITY_THRESHOLD:
                winners[resource] = sides[0][0]
            else:
                needs_escalation.append(resource)
        return winners, needs_escalation

    # -- COMMIT (with Finance veto enforcement) ----------------------------

    def _commit_all(
        self, proposals: list[Proposal], blackboard_state: BlackboardState
    ) -> dict[str, Any]:
        """No conflicts this tick: every non-abstaining proposal is a commit candidate."""
        to_commit = [p for p in proposals if p.action != "abstain"]
        return self._commit(to_commit, proposals, blackboard_state)

    def _commit_winners(
        self,
        winners: dict[str, str],
        proposals: list[Proposal],
        blackboard_state: BlackboardState,
    ) -> dict[str, Any]:
        """Apply the winning proposal per conflict, plus every proposal that
        was never part of any conflict, then enforce any surviving Finance veto."""
        proposals_by_agent = {p.agent: p for p in proposals}
        contested_resources = set(winners.keys())
        contesting_agents = {
            p.agent
            for p in proposals
            if p.action != "abstain" and p.target_resource in contested_resources
        }

        to_commit: list[Proposal] = []
        for winning_agent in winners.values():
            winner = proposals_by_agent.get(winning_agent)
            if winner is not None:
                to_commit.append(winner)
        for proposal in proposals:
            if proposal.action == "abstain" or proposal.agent in contesting_agents:
                continue
            to_commit.append(proposal)

        return self._commit(to_commit, proposals, blackboard_state)

    def _commit(
        self,
        to_commit: list[Proposal],
        all_proposals: list[Proposal],
        blackboard_state: BlackboardState,
    ) -> dict[str, Any]:
        vetoed_resources = self._active_vetoes(all_proposals)
        committed: list[dict[str, Any]] = []
        dropped: list[dict[str, Any]] = []
        for proposal in to_commit:
            if proposal.agent == "finance":
                continue  # Finance's own proposal is advisory, never a resource commit
            if proposal.target_resource in vetoed_resources:
                dropped.append(
                    {
                        "agent": proposal.agent,
                        "target_resource": proposal.target_resource,
                        "reason": "finance_veto",
                    }
                )
                continue
            committed.append(self._apply_commit(proposal, blackboard_state))
        return {"committed": committed, "vetoed": dropped}

    def _active_vetoes(self, proposals: list[Proposal]) -> set[str]:
        """Resource types Finance vetoed this tick that were not unanimously overridden."""
        finance_vetoes = {
            p.veto_target for p in proposals if p.agent == "finance" and p.veto and p.veto_target
        }
        if not finance_vetoes:
            return set()

        by_agent = {p.agent: p for p in proposals}
        unanimous_override = _NON_FINANCE_AGENTS.issubset(by_agent.keys()) and all(
            by_agent[name].action != "abstain"
            and by_agent[name].confidence >= OVERRIDE_CONFIDENCE_THRESHOLD
            for name in _NON_FINANCE_AGENTS
        )
        return set() if unanimous_override else finance_vetoes

    def _apply_commit(
        self, proposal: Proposal, blackboard_state: BlackboardState
    ) -> dict[str, Any]:
        """Deterministically apply one committed proposal to the blackboard:
        decrement the resource pool it drew from, spend its cost against the
        budget, and mark whatever casualty/trapped/tower record it served."""
        pool_field = _RESOURCE_POOL_FIELD.get(proposal.target_resource or "")
        if pool_field is not None:
            current = getattr(blackboard_state.resources, pool_field)
            setattr(blackboard_state.resources, pool_field, max(0, current - 1))
        if proposal.cost:
            blackboard_state.resources.budget_remaining = round(
                blackboard_state.resources.budget_remaining - proposal.cost, 2
            )
        self._mark_served(proposal, blackboard_state)
        return {
            "agent": proposal.agent,
            "action": proposal.action,
            "target_resource": proposal.target_resource,
            "cost": proposal.cost,
        }

    def _mark_served(self, proposal: Proposal, blackboard_state: BlackboardState) -> None:
        if proposal.agent == "medical" and proposal.action in (
            "request_helicopter_transport",
            "deploy_medic_team",
        ):
            untreated = [c for c in blackboard_state.casualties if not c.treated]
            if untreated:
                worst = max(untreated, key=lambda c: SEVERITY_RANK.get(c.severity, 0))
                worst.treated = True
        elif proposal.agent == "sar" and proposal.action in (
            "request_helicopter_transport",
            "deploy_sar_team",
        ):
            unrescued = [t for t in blackboard_state.trapped if not t.rescued]
            if unrescued:
                most_urgent = min(unrescued, key=lambda t: t.window_ends_tick)
                most_urgent.rescued = True
        elif proposal.agent == "comms" and proposal.action == "repair_tower":
            down = [t for t in blackboard_state.towers.values() if not t.operational]
            if down:
                down[0].operational = True
