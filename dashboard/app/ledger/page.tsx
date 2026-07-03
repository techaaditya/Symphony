"use client";

import { useEffect, useState } from "react";
import LedgerReplay from "@/components/LedgerReplay";
import { getLedger, startSim } from "@/lib/api";
import { useSimStream } from "@/hooks/useSimStream";
import type { LedgerEntry, SimMode } from "@/lib/types";

export default function LedgerPage() {
  const [simId, setSimId] = useState<string | null>(null);
  const [mode, setMode] = useState<SimMode>("society");
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [entries, setEntries] = useState<LedgerEntry[]>([]);

  // Drive the scenario to completion as fast as the server allows (interval_ms=0),
  // then fetch the canonical ledger once -- the replay view scrubs a finished run.
  const stream = useSimStream(simId, 0);

  useEffect(() => {
    if (simId && stream.finished) {
      getLedger(simId).then((res) => setEntries(res.entries));
    }
  }, [simId, stream.finished]);

  async function handleStart() {
    setStarting(true);
    setError(null);
    setEntries([]);
    try {
      const session = await startSim({ scenario_id: "wildfire_v3", seed: 42, mode });
      setSimId(session.sim_id);
    } catch {
      setError("Could not reach the Symphony API. Is it running on NEXT_PUBLIC_API_URL?");
    } finally {
      setStarting(false);
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-xl font-semibold text-text-primary">Ledger</h1>
        <select
          value={mode}
          onChange={(e) => setMode(e.target.value as SimMode)}
          disabled={!!simId}
          className="rounded-md border border-border bg-surface-1 px-2 py-1 text-sm text-text-primary"
        >
          <option value="society">Society (5 agents)</option>
          <option value="single_agent">Single-agent baseline</option>
        </select>
        <button
          onClick={handleStart}
          disabled={starting || (!!simId && !stream.finished)}
          className="rounded-md bg-text-primary px-3 py-1.5 text-sm font-medium text-page-plane disabled:opacity-40"
        >
          {simId && !stream.finished ? "Running…" : "Run scenario"}
        </button>
        {(error || stream.error) && (
          <span className="text-sm text-status-critical">{error ?? stream.error}</span>
        )}
      </div>
      <LedgerReplay entries={entries} mode={mode} />
    </div>
  );
}
