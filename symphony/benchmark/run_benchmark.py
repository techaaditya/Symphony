"""The benchmark harness (doc §10): run the five-agent society and the
single-agent baseline on identical scenarios and seeds, n trials each, and
report honest mean/SD comparisons across the four headline metrics.

No numbers from this module are ever committed to `results/` until a real run
has actually happened — see `responsible-ai.md`'s transparency commitment
that reported benchmark numbers are measured, not illustrative placeholders.
"""

from __future__ import annotations

import statistics
import tempfile
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from symphony.agents import (
    CommsAgent,
    Coordinator,
    FinanceAgent,
    LogisticsAgent,
    MedicalAgent,
    SarAgent,
)
from symphony.benchmark.metrics import compute_outcome
from symphony.benchmark.single_agent_baseline import run_single_agent_baseline
from symphony.benchmark.token_counter import TokenCountingProvider
from symphony.ledger.store import ConflictGraphHook, LedgerStore
from symphony.llm.provider import LLMProvider, get_provider
from symphony.protocol.parliament import ParliamentProtocol
from symphony.simulator.engine import load_scenario

if TYPE_CHECKING:
    from symphony.models import BlackboardState
    from symphony.simulator.engine import Simulator

_VALID_MODES = ("single_agent", "society")


def build_society(
    *,
    specialist_provider: LLMProvider | None = None,
    coordinator_provider: LLMProvider | None = None,
    ledger_path: str | Path | None = None,
    conflict_graph_hook: ConflictGraphHook | None = None,
) -> tuple[ParliamentProtocol, TokenCountingProvider, TokenCountingProvider]:
    """Construct one Parliament Protocol instance wired to token-counting
    providers, so `run_symphony_society`, the CLI's `sim` command, and the
    REST API's session registry (a later phase) can all share one
    construction path instead of duplicating agent/coordinator/ledger wiring.
    """
    specialists = TokenCountingProvider(specialist_provider or get_provider("specialist"))
    coordinator_backend = TokenCountingProvider(coordinator_provider or get_provider("coordinator"))
    agents = [
        LogisticsAgent(specialists),
        MedicalAgent(specialists),
        CommsAgent(specialists),
        FinanceAgent(specialists),
        SarAgent(specialists),
    ]
    coordinator = Coordinator(coordinator_backend)
    resolved_path = Path(ledger_path) if ledger_path else Path(tempfile.mktemp(suffix=".jsonl"))
    ledger = LedgerStore(resolved_path, conflict_graph_hook=conflict_graph_hook)
    protocol = ParliamentProtocol(agents, coordinator, ledger)
    return protocol, specialists, coordinator_backend


def run_symphony_society(
    sim: Simulator,
    *,
    specialist_provider: LLMProvider | None = None,
    coordinator_provider: LLMProvider | None = None,
) -> dict[str, Any]:
    """Run one full scenario through the five-agent Parliament Protocol;
    return its outcome in the same shape `run_single_agent_baseline` returns.
    """
    protocol, specialists, coordinator_backend = build_society(
        specialist_provider=specialist_provider, coordinator_provider=coordinator_provider
    )
    served_flags: list[bool | None] = []

    def round_runner(tick: int, state: BlackboardState) -> None:
        result = protocol.run_round(tick, state)
        served_flags.extend(c["served"] for c in result.outcome.get("committed", []))

    start = time.perf_counter()
    history = sim.run(round_runner)
    elapsed_s = time.perf_counter() - start

    total_tokens = specialists.total_tokens + coordinator_backend.total_tokens
    return compute_outcome(history[-1], served_flags, total_tokens, elapsed_s)


def run_benchmark(scenario_id: str, seed: int, n_trials: int, mode: str) -> dict[str, Any]:
    """mode: 'single_agent' or 'society'. The scenario is fixed across trials;
    the seed varies per trial (seed + trial index) so magnitudes differ while
    the event schedule doesn't — matching doc §10's harness exactly.
    """
    if mode not in _VALID_MODES:
        raise ValueError(f"Unknown benchmark mode: {mode!r}, expected one of {_VALID_MODES}")

    results: list[dict[str, Any]] = []
    for trial in range(n_trials):
        sim = load_scenario(scenario_id, seed=seed + trial)
        outcome = (
            run_single_agent_baseline(sim) if mode == "single_agent" else run_symphony_society(sim)
        )
        results.append(outcome)

    return {
        "mode": mode,
        "scenario_id": scenario_id,
        "n_trials": n_trials,
        "objectives_met_pct": _mean_sd(results, "objectives_met_pct"),
        "time_to_allocate_s": _mean_sd(results, "time_to_allocate_s"),
        "resource_waste_pct": _mean_sd(results, "resource_waste_pct"),
        "token_cost": _mean_sd(results, "token_cost"),
    }


def _mean_sd(results: list[dict[str, Any]], key: str) -> dict[str, float]:
    values = [r[key] for r in results]
    return {
        "mean": round(statistics.mean(values), 4),
        "sd": round(statistics.stdev(values), 4) if len(values) > 1 else 0.0,
    }


def compare_modes(scenario_id: str, seed: int, n_trials: int) -> dict[str, Any]:
    """Run both benchmark modes on identical seeds; return both summaries side
    by side for the CLI/API/dashboard comparison view.
    """
    return {
        "single_agent": run_benchmark(scenario_id, seed, n_trials, "single_agent"),
        "society": run_benchmark(scenario_id, seed, n_trials, "society"),
    }
