"use client";

import { useState } from "react";
import BenchmarkChart from "@/components/BenchmarkChart";
import { compareModes } from "@/lib/api";
import type { BenchmarkCompareResult } from "@/lib/types";

export default function BenchmarkPage() {
  const [seed, setSeed] = useState(42);
  const [nTrials, setNTrials] = useState(5);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<BenchmarkCompareResult | null>(null);

  async function handleRun() {
    setLoading(true);
    setError(null);
    try {
      const comparison = await compareModes("wildfire_v3", seed, nTrials);
      setResult(comparison);
    } catch {
      setError("Could not reach the Symphony API. Is it running on NEXT_PUBLIC_API_URL?");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="font-serif text-2xl font-semibold text-text-primary">Benchmark</h1>
        <label className="flex items-center gap-2 text-sm text-text-secondary">
          Seed
          <input
            type="number"
            value={seed}
            onChange={(e) => setSeed(Number(e.target.value))}
            className="w-20 rounded-md border border-border bg-surface-1 px-2 py-1 text-sm text-text-primary"
          />
        </label>
        <label className="flex items-center gap-2 text-sm text-text-secondary">
          Trials
          <input
            type="number"
            min={1}
            max={50}
            value={nTrials}
            onChange={(e) => setNTrials(Number(e.target.value))}
            className="w-16 rounded-md border border-border bg-surface-1 px-2 py-1 text-sm text-text-primary"
          />
        </label>
        <button
          onClick={handleRun}
          disabled={loading}
          className="rounded-md bg-accent px-3 py-1.5 text-sm font-medium text-accent-contrast transition-all duration-200 hover:bg-accent-hover disabled:opacity-40"
        >
          {loading ? "Running…" : "Run comparison"}
        </button>
        {error && <span className="text-sm text-status-critical">{error}</span>}
      </div>

      {result ? (
        <BenchmarkChart result={result} />
      ) : (
        <div className="card-panel flex h-40 items-center justify-center rounded-lg text-sm text-text-muted">
          Run a comparison to see society vs single-agent metrics.
        </div>
      )}
    </div>
  );
}
