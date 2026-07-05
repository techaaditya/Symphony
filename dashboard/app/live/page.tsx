"use client";

import dynamic from "next/dynamic";
import { useState } from "react";
import CollaborativeGrid from "@/components/CollaborativeGrid";
import { startSim } from "@/lib/api";
import { useSimStream } from "@/hooks/useSimStream";
import type { SimMode } from "@/lib/types";

// Leaflet touches `window` at module-eval time, so the map must never be
// part of the server-rendered bundle.
const DisasterMap = dynamic(() => import("@/components/DisasterMap"), { ssr: false });

export default function LivePage() {
  const [simId, setSimId] = useState<string | null>(null);
  const [mode, setMode] = useState<SimMode>("society");
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const stream = useSimStream(simId, 400);

  async function handleStart() {
    setStarting(true);
    setError(null);
    try {
      const session = await startSim({ scenario_id: "wildfire_v3", seed: 42, mode });
      setSimId(session.sim_id);
    } catch {
      setError("Could not reach the Symphony API. Is it running on NEXT_PUBLIC_API_URL?");
    } finally {
      setStarting(false);
    }
  }

  const worldState = stream.latest?.world_state ?? null;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="font-serif text-2xl font-semibold text-text-primary">Live</h1>
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
          className="rounded-md bg-accent px-3 py-1.5 text-sm font-medium text-accent-contrast transition-all duration-200 hover:bg-accent-hover disabled:opacity-40"
        >
          {simId && !stream.finished ? "Running…" : "Start scenario"}
        </button>
        {stream.finished && <span className="text-sm text-status-good">Run complete</span>}
        {(error || stream.error) && (
          <span className="text-sm text-status-critical">{error ?? stream.error}</span>
        )}
        <span className="ml-auto text-sm text-text-secondary">
          Tick {stream.latest?.tick ?? 0}
        </span>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="flex flex-col gap-2">
          <h2 className="text-sm font-medium text-text-secondary">Disaster map</h2>
          <DisasterMap worldState={worldState} />
        </div>
        <div className="flex flex-col gap-2">
          <h2 className="text-sm font-medium text-text-secondary">Command matrix</h2>
          <CollaborativeGrid latest={stream.latest} />
        </div>
      </div>
    </div>
  );
}
