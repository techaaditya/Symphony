"""`GET /conflicts/graph` (doc §8/§12): the subgraph of Proposal/Agent nodes
and CONFLICTED_WITH edges involving one agent, for the Conflict Graph
Explorer dashboard view.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from symphony.api.schemas import ConflictGraphResponse
from symphony.api.state import get_session

router = APIRouter(prefix="/conflicts", tags=["conflicts"])


@router.get("/graph", response_model=ConflictGraphResponse)
def conflicts_graph(sim_id: str, agent: str) -> ConflictGraphResponse:
    try:
        session = get_session(sim_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="unknown sim_id") from exc
    return ConflictGraphResponse(**session.conflict_graph.subgraph_for_agent(agent))
