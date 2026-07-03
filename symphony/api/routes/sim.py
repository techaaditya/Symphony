"""`/sim/*` endpoints (doc §12): start a session, advance it one tick at a
time, and read back its ledger.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from symphony.api.schemas import (
    SimLedgerResponse,
    SimStartRequest,
    SimStartResponse,
    SimTickRequest,
    SimTickResponse,
)
from symphony.api.state import create_session, get_session

router = APIRouter(prefix="/sim", tags=["sim"])


@router.post("/start", response_model=SimStartResponse)
def start_sim(request: SimStartRequest) -> SimStartResponse:
    session = create_session(request.scenario_id, request.seed, request.mode)
    return SimStartResponse(
        sim_id=session.sim_id,
        scenario_id=session.scenario_id,
        seed=session.seed,
        mode=session.mode,
        ticks_total=session.sim.ticks_total,
    )


@router.post("/tick", response_model=SimTickResponse)
def tick_sim(request: SimTickRequest) -> SimTickResponse:
    try:
        session = get_session(request.sim_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="unknown sim_id") from exc
    if session.finished:
        raise HTTPException(status_code=409, detail="scenario already finished")

    result = session.run_tick()
    return SimTickResponse(
        sim_id=request.sim_id, tick=session.current_tick, finished=session.finished, result=result
    )


@router.get("/ledger", response_model=SimLedgerResponse)
def get_ledger(sim_id: str) -> SimLedgerResponse:
    try:
        session = get_session(sim_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="unknown sim_id") from exc

    if session.mode == "society":
        assert session.protocol is not None
        entries = session.protocol.ledger.read_all()
    else:
        entries = session.baseline_log
    return SimLedgerResponse(sim_id=sim_id, mode=session.mode, entries=entries)
