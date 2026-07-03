"""`/benchmark/*` endpoints (doc §10/§12): run the harness and the
society-vs-single-agent comparison over HTTP.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from symphony.api.schemas import BenchmarkCompareRequest, BenchmarkRunRequest
from symphony.benchmark.run_benchmark import compare_modes, run_benchmark

router = APIRouter(prefix="/benchmark", tags=["benchmark"])


@router.post("/run")
def run(request: BenchmarkRunRequest) -> dict[str, Any]:
    return run_benchmark(request.scenario_id, request.seed, request.n_trials, request.mode)


@router.post("/compare")
def compare(request: BenchmarkCompareRequest) -> dict[str, Any]:
    return compare_modes(request.scenario_id, request.seed, request.n_trials)
