"""Pydantic request/response models for the REST API (doc §12)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel


class SimStartRequest(BaseModel):
    scenario_id: str = "wildfire_v3"
    seed: int = 42
    mode: Literal["society", "single_agent"] = "society"


class SimStartResponse(BaseModel):
    sim_id: str
    scenario_id: str
    seed: int
    mode: str
    ticks_total: int


class SimTickRequest(BaseModel):
    sim_id: str


class SimTickResponse(BaseModel):
    sim_id: str
    tick: int
    finished: bool
    result: dict[str, Any]


class SimLedgerResponse(BaseModel):
    sim_id: str
    mode: str
    entries: list[dict[str, Any]]


class BenchmarkRunRequest(BaseModel):
    scenario_id: str = "wildfire_v3"
    seed: int = 42
    n_trials: int = 20
    mode: Literal["society", "single_agent"]


class BenchmarkCompareRequest(BaseModel):
    scenario_id: str = "wildfire_v3"
    seed: int = 42
    n_trials: int = 20


class ConflictGraphResponse(BaseModel):
    agents: list[dict[str, Any]]
    proposals: list[dict[str, Any]]
    edges: list[dict[str, Any]]
