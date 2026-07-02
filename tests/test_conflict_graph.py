"""Doc §15's conflict-graph write test: confirm every detected conflict
actually produces a CONFLICTED_WITH edge, so the Conflict Graph Explorer isn't
demoing an empty graph. Exercises the default JSON writer end to end (via
LedgerStore's hook) plus the writer's own node/edge/subgraph behaviour
directly — no database required.
"""

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
from symphony.config import ConflictGraphConfig
from symphony.ledger.store import LedgerStore
from symphony.llm.provider import MockProvider
from symphony.models import (
    BlackboardState,
    CasualtyReport,
    Proposal,
    ResourcePools,
    Tower,
    TrappedReport,
    Zone,
)
from symphony.protocol.conflict_graph import JsonConflictGraphWriter, get_conflict_graph_writer
from symphony.protocol.parliament import ParliamentProtocol


def _tmp_json_path() -> Path:
    return Path(tempfile.mktemp(suffix=".json"))


def _proposal(agent: str, resource: str) -> Proposal:
    return Proposal(
        agent=agent, action="a", target_resource=resource, rationale="r", confidence=0.5
    )


def _blackboard(*, budget: float = 500_000.0) -> BlackboardState:
    return BlackboardState(
        tick=4,
        zones={
            "zone-1": Zone(id="zone-1", name="Ridgeline District", lat=38.90, lng=-120.98),
            "zone-2": Zone(id="zone-2", name="Lakeview Basin", lat=38.85, lng=-121.05),
        },
        resources=ResourcePools(
            helicopters=2, medic_teams=3, sar_teams=2, comms_towers=2, budget_remaining=budget
        ),
        towers={
            "tower-1": Tower(id="tower-1", zone_id="zone-1"),
            "tower-2": Tower(id="tower-2", zone_id="zone-2"),
        },
        casualties=[CasualtyReport(zone_id="zone-2", count=5, severity="serious", tick_reported=4)],
        trapped=[TrappedReport(zone_id="zone-2", count=3, tick_reported=4, window_ends_tick=8)],
    )


def _run_round_with_writer(writer: JsonConflictGraphWriter) -> None:
    provider = MockProvider(seed=42)
    agents = [
        LogisticsAgent(provider),
        MedicalAgent(provider),
        CommsAgent(provider),
        FinanceAgent(provider),
        SarAgent(provider),
    ]
    coordinator = Coordinator(provider)
    ledger = LedgerStore(
        Path(tempfile.mktemp(suffix=".jsonl")), conflict_graph_hook=writer.record_conflict
    )
    protocol = ParliamentProtocol(agents, coordinator, ledger)
    protocol.run_round(4, _blackboard())


def test_every_detected_conflict_produces_a_conflicted_with_edge() -> None:
    writer = JsonConflictGraphWriter(_tmp_json_path())
    _run_round_with_writer(writer)

    graph = writer._read()
    assert len(graph["edges"]) >= 1
    edge = graph["edges"][0]
    assert edge["resource"] == "helicopter"
    assert edge["outcome"] in {"medical", "sar"}

    edge_agents = set()
    for proposal in graph["proposals"]:
        if proposal["id"] in (edge["source"], edge["target"]):
            edge_agents.add(proposal["agent"])
    assert edge_agents == {"medical", "sar"}


def test_conflict_with_no_edges_when_no_conflict_occurs() -> None:
    writer = JsonConflictGraphWriter(_tmp_json_path())
    provider = MockProvider(seed=42)
    agents = [
        LogisticsAgent(provider),
        MedicalAgent(provider),
        CommsAgent(provider),
        FinanceAgent(provider),
        SarAgent(provider),
    ]
    coordinator = Coordinator(provider)
    ledger = LedgerStore(
        Path(tempfile.mktemp(suffix=".jsonl")), conflict_graph_hook=writer.record_conflict
    )
    protocol = ParliamentProtocol(agents, coordinator, ledger)

    blackboard = _blackboard()
    blackboard.casualties = []
    blackboard.trapped = []
    protocol.run_round(4, blackboard)

    assert writer._read()["edges"] == []


def test_record_conflict_creates_one_edge_per_pair_for_three_way_conflict() -> None:
    writer = JsonConflictGraphWriter(_tmp_json_path())
    proposals = [
        _proposal("medical", "helicopter"),
        _proposal("sar", "helicopter"),
        _proposal("logistics", "helicopter"),
    ]

    writer.record_conflict(1, "helicopter", proposals, "medical")

    graph = writer._read()
    assert len(graph["proposals"]) == 3
    assert len(graph["edges"]) == 3  # C(3, 2) pairwise edges
    assert all(e["outcome"] == "medical" for e in graph["edges"])


def test_subgraph_for_agent_only_returns_edges_involving_that_agent() -> None:
    writer = JsonConflictGraphWriter(_tmp_json_path())
    helicopter_proposals = [_proposal("medical", "helicopter"), _proposal("sar", "helicopter")]
    tower_proposals = [_proposal("comms", "comms_tower"), _proposal("logistics", "comms_tower")]
    writer.record_conflict(1, "helicopter", helicopter_proposals, "medical")
    writer.record_conflict(1, "comms_tower", tower_proposals, "comms")

    subgraph = writer.subgraph_for_agent("medical")

    assert {a["name"] for a in subgraph["agents"]} == {"medical", "sar"}
    assert len(subgraph["edges"]) == 1
    assert subgraph["edges"][0]["resource"] == "helicopter"


def test_subgraph_for_agent_not_involved_in_any_conflict_is_empty() -> None:
    writer = JsonConflictGraphWriter(_tmp_json_path())
    proposals = [_proposal("medical", "helicopter"), _proposal("sar", "helicopter")]
    writer.record_conflict(1, "helicopter", proposals, "medical")

    subgraph = writer.subgraph_for_agent("finance")

    assert subgraph == {"agents": [], "proposals": [], "edges": []}


def test_ledger_hook_reports_vetoed_outcome_when_veto_holds() -> None:
    # seed=1 under a tight budget reproducibly yields a genuine two-way
    # Medical-vs-SAR "helicopter" conflict where Finance's veto holds (SAR's
    # confidence stays below the override threshold) — the same seed relied
    # on in tests/test_veto.py, empirically chosen so this is a real
    # conflict-graph edge, not a solo proposal Finance quietly vetoes.
    writer = JsonConflictGraphWriter(_tmp_json_path())
    provider = MockProvider(seed=1)
    agents = [
        LogisticsAgent(provider),
        MedicalAgent(provider),
        CommsAgent(provider),
        FinanceAgent(provider),
        SarAgent(provider),
    ]
    coordinator = Coordinator(provider)
    ledger = LedgerStore(
        Path(tempfile.mktemp(suffix=".jsonl")), conflict_graph_hook=writer.record_conflict
    )
    protocol = ParliamentProtocol(agents, coordinator, ledger)

    protocol.run_round(4, _blackboard(budget=5_000.0))

    graph = writer._read()
    helicopter_edges = [e for e in graph["edges"] if e["resource"] == "helicopter"]
    assert helicopter_edges
    assert all(e["outcome"] == "vetoed" for e in helicopter_edges)


def test_factory_returns_json_writer_by_default() -> None:
    config = ConflictGraphConfig(json_path=str(_tmp_json_path()))
    writer = get_conflict_graph_writer(config)
    assert isinstance(writer, JsonConflictGraphWriter)
