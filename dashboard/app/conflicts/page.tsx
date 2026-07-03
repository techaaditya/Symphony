"use client";

import { useEffect, useState } from "react";
import ConflictGraph from "@/components/ConflictGraph";
import { getConflictGraph, startSim } from "@/lib/api";
import { AGENT_ORDER, agentColor, useThemePalette } from "@/lib/colors";
import { useSimStream } from "@/hooks/useSimStream";
import type { ConflictGraphResponse } from "@/lib/types";

export default function ConflictsPage() {
  const [simId, setSimId] = useState<string | null>(null);
  const [agent, setAgent] = useState<string>(AGENT_ORDER[0]);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [graph, setGraph] = useState<ConflictGraphResponse | null>(null);
  const palette = useThemePalette();

  // Conflict recording only happens in society mode -- the baseline never
  // touches the conflict-graph hook (symphony/api/state.py).
  const stream = useSimStream(simId, 0);

  useEffect(() => {
    if (simId && stream.finished) {
      getConflictGraph(simId, agent).then(setGraph);
    }
  }, [simId, stream.finished, agent]);

  async function handleStart() {
    setStarting(true);
    setError(null);
    setGraph(null);
    try {
      const session = await startSim({ scenario_id: "wildfire_v3", seed: 42, mode: "society" });
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
        <h1 className="text-xl font-semibold text-text-primary">Conflicts</h1>
        <button
          onClick={handleStart}
          disabled={starting || (!!simId && !stream.finished)}
          className="rounded-md bg-text-primary px-3 py-1.5 text-sm font-medium text-page-plane disabled:opacity-40"
        >
          {simId && !stream.finished ? "Running…" : "Run scenario"}
        </button>
        <label className="flex items-center gap-2 text-sm text-text-secondary">
          Focus agent
          <select
            value={agent}
            onChange={(e) => setAgent(e.target.value)}
            className="rounded-md border border-border bg-surface-1 px-2 py-1 text-sm text-text-primary capitalize"
          >
            {AGENT_ORDER.map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
        </label>
        {(error || stream.error) && (
          <span className="text-sm text-status-critical">{error ?? stream.error}</span>
        )}
      </div>

      <ConflictGraph graph={graph} focusAgent={agent} />

      <div className="flex flex-wrap gap-x-4 gap-y-1">
        {AGENT_ORDER.map((name) => (
          <span key={name} className="flex items-center gap-1.5 text-xs text-text-secondary">
            <span className="h-2.5 w-2.5 rounded-full" style={{ background: agentColor(palette, name) }} />
            <span className="capitalize">{name}</span>
          </span>
        ))}
      </div>
    </div>
  );
}
