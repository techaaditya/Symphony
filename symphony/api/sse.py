"""`GET /sim/stream` (doc §12/§18): auto-advances a session tick by tick,
emitting one Server-Sent Event per tick, for the dashboard's live map and
agent graph. `interval_ms` paces the demo (default 300ms between ticks);
pass 0 for an instant, back-to-back replay (used by the test suite).
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from symphony.api.state import get_session

router = APIRouter(prefix="/sim", tags=["sim"])


@router.get("/stream")
async def stream_sim(sim_id: str, interval_ms: int = 300) -> EventSourceResponse:
    try:
        session = get_session(sim_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="unknown sim_id") from exc

    async def event_generator() -> AsyncIterator[dict[str, Any]]:
        while not session.finished:
            result = session.run_tick()
            yield {"event": "tick", "data": json.dumps(result, default=str)}
            if interval_ms:
                await asyncio.sleep(interval_ms / 1000)
        yield {"event": "done", "data": json.dumps({"sim_id": sim_id})}

    return EventSourceResponse(event_generator())
