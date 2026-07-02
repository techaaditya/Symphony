"""Conflict Graph Explorer writer (doc §8): every detected conflict becomes a
small graph of who proposed what and who clashed with whom.

Two implementations share one interface. `JsonConflictGraphWriter` is the
zero-config default — it appends to a local JSON file, so the abstention/
escalation/veto test suite and a demo run both exercise the real code path
with no database. `Neo4jConflictGraphWriter` activates when `NEO4J_URI` is
set and runs the exact `MERGE` pattern from the doc:

    MERGE (a1:Agent {name: $agent1})-[:PROPOSED]->(p1:Proposal {...})
    MERGE (a2:Agent {name: $agent2})-[:PROPOSED]->(p2:Proposal {...})
    MERGE (p1)-[:CONFLICTED_WITH {resource: $resource, outcome: $outcome}]->(p2)

Both back the same `/conflicts/graph?agent=...` subgraph query (doc §12), so
the API layer (a later phase) can ask either backend for "every conflict
`agent` was party to" without knowing which one is live.
"""

from __future__ import annotations

import itertools
import json
from pathlib import Path
from typing import Any, Protocol

from symphony.config import ConflictGraphConfig, get_config
from symphony.models import Proposal


class ConflictGraphWriter(Protocol):
    """Records conflicts and answers the per-agent subgraph query (doc §8/§12)."""

    def record_conflict(
        self, tick: int, resource: str, proposals: list[Proposal], outcome: str
    ) -> None: ...

    def subgraph_for_agent(self, agent: str) -> dict[str, Any]: ...


def _proposal_id(tick: int, agent: str, resource: str) -> str:
    return f"{tick}:{agent}:{resource}"


class JsonConflictGraphWriter:
    """Default backend: appends nodes/edges to a local JSON file. No DB required."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write({"agents": [], "proposals": [], "edges": []})

    def _read(self) -> dict[str, Any]:
        with self.path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def _write(self, graph: dict[str, Any]) -> None:
        with self.path.open("w", encoding="utf-8") as f:
            json.dump(graph, f, indent=2)

    def record_conflict(
        self, tick: int, resource: str, proposals: list[Proposal], outcome: str
    ) -> None:
        graph = self._read()
        agent_names = {a["name"] for a in graph["agents"]}
        proposal_ids = {p["id"] for p in graph["proposals"]}

        for proposal in proposals:
            if proposal.agent not in agent_names:
                graph["agents"].append({"name": proposal.agent})
                agent_names.add(proposal.agent)

            proposal_id = _proposal_id(tick, proposal.agent, resource)
            if proposal_id not in proposal_ids:
                graph["proposals"].append(
                    {
                        "id": proposal_id,
                        "agent": proposal.agent,
                        "tick": tick,
                        "rationale": proposal.rationale,
                    }
                )
                proposal_ids.add(proposal_id)

        # A conflict with N proposals fans out to every pairwise CONFLICTED_WITH
        # edge, matching the doc §8 pattern (defined for a pair) generalized to
        # the N > 2 case (e.g. three agents all wanting "helicopter").
        for left, right in itertools.combinations(proposals, 2):
            graph["edges"].append(
                {
                    "source": _proposal_id(tick, left.agent, resource),
                    "target": _proposal_id(tick, right.agent, resource),
                    "resource": resource,
                    "outcome": outcome,
                    "tick": tick,
                }
            )

        self._write(graph)

    def subgraph_for_agent(self, agent: str) -> dict[str, Any]:
        """All Proposal/Agent nodes and CONFLICTED_WITH edges involving `agent`."""
        graph = self._read()
        agent_proposal_ids = {p["id"] for p in graph["proposals"] if p["agent"] == agent}
        edges = [
            e
            for e in graph["edges"]
            if e["source"] in agent_proposal_ids or e["target"] in agent_proposal_ids
        ]
        involved_ids = {e["source"] for e in edges} | {e["target"] for e in edges}
        proposals = [p for p in graph["proposals"] if p["id"] in involved_ids]
        agent_names = {p["agent"] for p in proposals}
        return {
            "agents": [a for a in graph["agents"] if a["name"] in agent_names],
            "proposals": proposals,
            "edges": edges,
        }


class Neo4jConflictGraphWriter:
    """Real backend: MERGEs the doc §8 Cypher pattern into Neo4j. Activated via NEO4J_URI."""

    def __init__(self, uri: str, user: str, password: str) -> None:
        from neo4j import GraphDatabase  # optional dependency, imported lazily

        self._driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self) -> None:
        self._driver.close()

    def record_conflict(
        self, tick: int, resource: str, proposals: list[Proposal], outcome: str
    ) -> None:
        with self._driver.session() as session:
            for left, right in itertools.combinations(proposals, 2):
                session.run(
                    """
                    MERGE (a1:Agent {name: $agent1})-[:PROPOSED]->
                        (p1:Proposal {id: $proposal1_id, tick: $tick, rationale: $rationale1})
                    MERGE (a2:Agent {name: $agent2})-[:PROPOSED]->
                        (p2:Proposal {id: $proposal2_id, tick: $tick, rationale: $rationale2})
                    MERGE (p1)-[:CONFLICTED_WITH {resource: $resource, outcome: $outcome}]->(p2)
                    """,
                    agent1=left.agent,
                    proposal1_id=_proposal_id(tick, left.agent, resource),
                    rationale1=left.rationale,
                    agent2=right.agent,
                    proposal2_id=_proposal_id(tick, right.agent, resource),
                    rationale2=right.rationale,
                    tick=tick,
                    resource=resource,
                    outcome=outcome,
                )

    def subgraph_for_agent(self, agent: str) -> dict[str, Any]:
        with self._driver.session() as session:
            records = list(
                session.run(
                    """
                    MATCH (a:Agent {name: $agent})-[:PROPOSED]->(p:Proposal)
                    MATCH (p)-[r:CONFLICTED_WITH]-(other:Proposal)<-[:PROPOSED]-(oa:Agent)
                    RETURN a.name AS agent, p AS proposal, oa.name AS other_agent,
                           other AS other_proposal, r AS edge
                    """,
                    agent=agent,
                )
            )

        agents: dict[str, dict[str, Any]] = {}
        proposals: dict[str, dict[str, Any]] = {}
        edges: list[dict[str, Any]] = []
        for record in records:
            agents[record["agent"]] = {"name": record["agent"]}
            agents[record["other_agent"]] = {"name": record["other_agent"]}

            proposal, other_proposal = record["proposal"], record["other_proposal"]
            proposals[proposal["id"]] = {**dict(proposal), "agent": record["agent"]}
            proposals[other_proposal["id"]] = {
                **dict(other_proposal),
                "agent": record["other_agent"],
            }

            edge = record["edge"]
            edges.append(
                {
                    "source": proposal["id"],
                    "target": other_proposal["id"],
                    "resource": edge["resource"],
                    "outcome": edge["outcome"],
                    "tick": proposal["tick"],
                }
            )

        return {
            "agents": list(agents.values()),
            "proposals": list(proposals.values()),
            "edges": edges,
        }


def get_conflict_graph_writer(
    config: ConflictGraphConfig | None = None,
) -> ConflictGraphWriter:
    """Build the conflict-graph writer selected by config (Neo4j if NEO4J_URI is set)."""
    config = config or get_config().conflict_graph
    if config.backend == "neo4j":
        return Neo4jConflictGraphWriter(config.neo4j_uri, config.neo4j_user, config.neo4j_password)
    return JsonConflictGraphWriter(config.json_path)
