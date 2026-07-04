#!/usr/bin/env python3
"""Scripted demo driver (docs/demo-script.md): starts a scenario against a
running Symphony API and advances it one tick at a time at a pace suited to
narrating over a screen recording of the dashboard's Live view -- rather
than clicking "Start scenario" and hoping the timing lines up.

Uses only the standard library (no `requests`/`httpx`) so it runs against
any Python 3.11+ with zero extra installs, against whatever's already
running via `make up` or a real Alibaba Cloud deploy.

Usage:
    python scripts/demo_run.py
    python scripts/demo_run.py --host http://<ecs-ip>:8000 --seed 42 --pace 1.5
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.request
from typing import Any


def _post(host: str, path: str, payload: dict[str, Any]) -> dict[str, Any]:
    request = urllib.request.Request(
        f"{host}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request) as response:
        return json.loads(response.read())


def run(host: str, scenario_id: str, seed: int, mode: str, pace: float) -> None:
    session = _post(
        host, "/sim/start", {"scenario_id": scenario_id, "seed": seed, "mode": mode}
    )
    sim_id = session["sim_id"]
    print(f"started {mode} run: sim_id={sim_id} scenario={scenario_id} seed={seed}")
    print("dashboard: http://localhost:3000/live (this sim_id isn't selectable there yet --")
    print("open /live and click Start scenario there too, or watch this terminal instead)\n")

    finished = False
    while not finished:
        result = _post(host, "/sim/tick", {"sim_id": sim_id})
        finished = result["finished"]
        tick = result["tick"]
        payload = result["result"]

        if "proposals" in payload:
            conflicts = list(payload["conflicts"].keys()) or "none"
            committed = [c["agent"] for c in payload["outcome"].get("committed", [])]
            vetoed = [v["agent"] for v in payload["outcome"].get("vetoed", [])]
            print(
                f"tick {tick:>2}: conflicts={conflicts} escalated={payload['escalated']} "
                f"committed={committed} vetoed={vetoed}"
            )
        else:
            committed = payload.get("committed")
            print(f"tick {tick:>2}: generalist committed={committed}")

        time.sleep(pace)

    print(f"\nrun finished. Ledger: GET {host}/sim/ledger?sim_id={sim_id}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="http://localhost:8000")
    parser.add_argument("--scenario", default="wildfire_v3")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--mode", choices=["society", "single_agent"], default="society")
    parser.add_argument(
        "--pace", type=float, default=1.0, help="Seconds to wait between ticks (demo pacing)."
    )
    args = parser.parse_args()
    run(args.host, args.scenario, args.seed, args.mode, args.pace)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
