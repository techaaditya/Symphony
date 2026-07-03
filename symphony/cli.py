"""Symphony's command-line entry points.

`symphony sim` runs one scenario and prints the tick-by-tick deliberation
transcript (conflicts, escalations, vetoes, commits) for either mode.
`symphony benchmark` runs the full society-vs-single-agent comparison (doc
§10) and prints a summary table. Both run entirely offline against the
deterministic mock provider unless `SYMPHONY_LLM=qwen` is configured.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from symphony.benchmark.metrics import compute_outcome
from symphony.benchmark.run_benchmark import build_society, compare_modes
from symphony.benchmark.single_agent_baseline import run_single_agent_baseline
from symphony.models import BlackboardState
from symphony.simulator.engine import load_scenario


def _cmd_sim(args: argparse.Namespace) -> None:
    sim = load_scenario(args.scenario, seed=args.seed)
    if args.ticks is not None:
        sim.ticks_total = min(args.ticks, sim.ticks_total)

    if args.mode == "single_agent":
        outcome = run_single_agent_baseline(sim)
        print(json.dumps({"mode": "single_agent", "outcome": outcome}, indent=2))
        return

    protocol, specialists, coordinator_backend = build_society(ledger_path=args.ledger_path)
    served_flags: list[bool | None] = []

    def round_runner(tick: int, state: BlackboardState) -> None:
        result = protocol.run_round(tick, state)
        served_flags.extend(c["served"] for c in result.outcome.get("committed", []))
        conflicts = list(result.conflicts.keys())
        committed = [c["agent"] for c in result.outcome.get("committed", [])]
        vetoed = [v["agent"] for v in result.outcome.get("vetoed", [])]
        print(
            f"tick {tick:>2}: conflicts={conflicts or 'none'} escalated={result.escalated} "
            f"committed={committed} vetoed={vetoed}"
        )

    import time

    start = time.perf_counter()
    history = sim.run(round_runner)
    elapsed_s = time.perf_counter() - start

    total_tokens = specialists.total_tokens + coordinator_backend.total_tokens
    outcome = compute_outcome(history[-1], served_flags, total_tokens, elapsed_s)
    print(f"\nledger written to: {protocol.ledger.path}")
    print(json.dumps({"mode": "society", "outcome": outcome}, indent=2))


def _cmd_benchmark(args: argparse.Namespace) -> None:
    comparison = compare_modes(args.scenario, args.seed, args.n)
    _print_comparison_table(comparison)
    if args.json:
        print(json.dumps(comparison, indent=2))


def _print_comparison_table(comparison: dict[str, Any]) -> None:
    single = comparison["single_agent"]
    society = comparison["society"]
    metrics = ["objectives_met_pct", "time_to_allocate_s", "resource_waste_pct", "token_cost"]
    header = f"{'metric':<22}{'single_agent':<24}{'society':<24}"
    print(header)
    print("-" * len(header))
    for metric in metrics:
        single_cell = f"{single[metric]['mean']:.2f} (sd {single[metric]['sd']:.2f})"
        society_cell = f"{society[metric]['mean']:.2f} (sd {society[metric]['sd']:.2f})"
        print(f"{metric:<22}{single_cell:<24}{society_cell:<24}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="symphony")
    subparsers = parser.add_subparsers(dest="command", required=True)

    sim_parser = subparsers.add_parser("sim", help="Run one scenario and print its transcript.")
    sim_parser.add_argument("--scenario", default="wildfire_v3")
    sim_parser.add_argument("--seed", type=int, default=42)
    sim_parser.add_argument("--ticks", type=int, default=None, help="Stop after N ticks.")
    sim_parser.add_argument("--mode", choices=["society", "single_agent"], default="society")
    sim_parser.add_argument("--ledger-path", default=None)
    sim_parser.set_defaults(func=_cmd_sim)

    bench_parser = subparsers.add_parser(
        "benchmark", help="Run the society-vs-single-agent benchmark comparison."
    )
    bench_parser.add_argument("--scenario", default="wildfire_v3")
    bench_parser.add_argument("--seed", type=int, default=42)
    bench_parser.add_argument("--n", type=int, default=20, help="Trials per mode.")
    bench_parser.add_argument("--json", action="store_true", help="Also print raw JSON output.")
    bench_parser.set_defaults(func=_cmd_benchmark)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
