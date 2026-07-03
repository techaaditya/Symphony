"""In-memory sim-session registry backing the REST API (doc §12).

Each `POST /sim/start` call creates one `SimSession` scoped to a `sim_id`;
every other `/sim/*` and `/conflicts/*` endpoint looks the session up by that
id. The registry is process-local and unpersisted by design — it exists to
back a dashboard/demo session, not as a durable store. The ledger and
conflict-graph JSON files a session writes to disk are the durable artifacts
of a run, same as a CLI-driven `symphony sim` invocation.
"""

from __future__ import annotations

import tempfile
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from symphony.benchmark.run_benchmark import build_society
from symphony.benchmark.single_agent_baseline import SingleAgentBaseline
from symphony.llm.provider import get_provider
from symphony.models import RoundResult
from symphony.protocol.conflict_graph import JsonConflictGraphWriter
from symphony.protocol.parliament import ParliamentProtocol
from symphony.simulator.engine import Simulator, load_scenario


@dataclass
class SimSession:
    """One running scenario, in either benchmark mode, tickable one step at a time."""

    sim_id: str
    scenario_id: str
    seed: int
    mode: str
    sim: Simulator
    conflict_graph: JsonConflictGraphWriter
    protocol: ParliamentProtocol | None = None
    baseline: SingleAgentBaseline | None = None
    baseline_log: list[dict[str, Any]] = field(default_factory=list)

    @property
    def current_tick(self) -> int:
        return self.sim.state.tick

    @property
    def finished(self) -> bool:
        return self.current_tick >= self.sim.ticks_total

    def run_tick(self) -> dict[str, Any]:
        """Advance exactly one tick and return that tick's result payload."""
        captured: list[Any] = []

        def round_runner(tick: int, state: Any) -> None:
            if self.mode == "society":
                assert self.protocol is not None
                captured.append(self.protocol.run_round(tick, state))
            else:
                assert self.baseline is not None
                captured.append(self.baseline.decide_and_commit(tick, state))

        self.sim.step(round_runner)

        if self.mode == "society":
            result: RoundResult = captured[0]
            payload = _round_result_payload(result)
        else:
            payload = {"tick": self.current_tick, "committed": captured[0]}
            self.baseline_log.append(payload)
        return payload


def _round_result_payload(result: RoundResult) -> dict[str, Any]:
    return {
        "tick": result.tick,
        "proposals": [_proposal_payload(p) for p in result.proposals],
        "conflicts": {
            resource: [_proposal_payload(p) for p in proposals]
            for resource, proposals in result.conflicts.items()
        },
        "debate_log": result.debate_log,
        "votes": result.votes,
        "outcome": result.outcome,
        "escalated": result.escalated,
    }


def _proposal_payload(proposal: Any) -> dict[str, Any]:
    return {
        "agent": proposal.agent,
        "action": proposal.action,
        "target_resource": proposal.target_resource,
        "rationale": proposal.rationale,
        "confidence": proposal.confidence,
        "veto": proposal.veto,
        "veto_target": proposal.veto_target,
        "cost": proposal.cost,
    }


_REGISTRY: dict[str, SimSession] = {}


def create_session(scenario_id: str, seed: int, mode: str) -> SimSession:
    sim_id = str(uuid.uuid4())
    sim = load_scenario(scenario_id, seed)

    session_dir = Path(tempfile.mkdtemp(prefix=f"symphony-{sim_id}-"))
    conflict_graph = JsonConflictGraphWriter(session_dir / "conflicts.json")

    protocol: ParliamentProtocol | None = None
    baseline: SingleAgentBaseline | None = None
    if mode == "society":
        protocol, _, _ = build_society(
            ledger_path=session_dir / "ledger.jsonl",
            conflict_graph_hook=conflict_graph.record_conflict,
        )
    else:
        baseline = SingleAgentBaseline(get_provider("specialist"))

    session = SimSession(
        sim_id=sim_id,
        scenario_id=scenario_id,
        seed=seed,
        mode=mode,
        sim=sim,
        conflict_graph=conflict_graph,
        protocol=protocol,
        baseline=baseline,
    )
    _REGISTRY[sim_id] = session
    return session


def get_session(sim_id: str) -> SimSession:
    session = _REGISTRY.get(sim_id)
    if session is None:
        raise KeyError(sim_id)
    return session


def reset_registry() -> None:
    """Test-only: clear every session between test runs."""
    _REGISTRY.clear()
