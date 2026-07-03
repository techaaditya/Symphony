"""FastAPI application (doc §12): exposes the Parliament Protocol, the
benchmark harness, and the Conflict Graph Explorer over HTTP for the
dashboard.

Requires the optional `api` extra (`pip install -e ".[api]"`); every other
part of Symphony — the simulator, agents, protocol, ledger, benchmark, and
CLI — runs without it.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from symphony.api.routes import benchmark, conflicts, sim
from symphony.api.sse import router as sse_router
from symphony.config import get_config


def create_app() -> FastAPI:
    config = get_config()
    app = FastAPI(
        title="Symphony API",
        version="0.1.0",
        description=(
            "Multi-agent crisis-response society. "
            '"Agents propose, deterministic code adjudicates."'
        ),
    )
    origins = [origin.strip() for origin in config.api_cors_origins.split(",") if origin.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(sim.router)
    app.include_router(sse_router)
    app.include_router(benchmark.router)
    app.include_router(conflicts.router)
    return app


app = create_app()
