"""Deliberation ledger: append-only JSONL record of every Parliament round.

Every round — including abstentions and Finance vetoes — is written here, in
keeping with the responsible-ai.md transparency commitment that "every
deliberation round... is logged to the ledger... nothing is a black box."
Each detected conflict is also fanned out to an injectable conflict-graph
hook, which `symphony.protocol.conflict_graph.ConflictGraphWriter.record_conflict`
plugs into directly (same signature, so a writer instance's bound method can be
passed as the hook with no adapter).
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path
from typing import Any

from symphony.models import Proposal, RoundResult

# Called once per detected conflict as a round is written: (tick, resource,
# proposals, outcome). `outcome` is the committed agent's name, "vetoed", or
# "unresolved" — read off the round's already-decided outcome, since the hook
# fires after COMMIT, not during CONFLICT_CHECK.
ConflictGraphHook = Callable[[int, str, list[Proposal], str], None]


class LedgerStore:
    """Appends each Parliament round to a JSONL file."""

    def __init__(
        self,
        path: str | Path,
        *,
        conflict_graph_hook: ConflictGraphHook | None = None,
    ) -> None:
        self.path = Path(path)
        self.conflict_graph_hook = conflict_graph_hook
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, result: RoundResult) -> None:
        """Append one round to the ledger and notify the conflict-graph hook."""
        record = asdict(result)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")

        if self.conflict_graph_hook is not None:
            committed_by_resource = {
                c["target_resource"]: c["agent"] for c in result.outcome.get("committed", [])
            }
            vetoed_resources = {v["target_resource"] for v in result.outcome.get("vetoed", [])}
            for resource, proposals in result.conflicts.items():
                if resource in committed_by_resource:
                    outcome = committed_by_resource[resource]
                elif resource in vetoed_resources:
                    outcome = "vetoed"
                else:
                    outcome = "unresolved"
                self.conflict_graph_hook(result.tick, resource, proposals, outcome)

    def read_all(self) -> list[dict[str, Any]]:
        """Read every ledger entry written so far, oldest first."""
        if not self.path.exists():
            return []
        with self.path.open("r", encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]
