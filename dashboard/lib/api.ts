/**
 * Typed client for the Symphony REST API (`symphony/api/`, doc §12).
 * Every function throws `ApiError` on a non-2xx response so callers can
 * branch on `status` (e.g. 404 unknown sim_id, 409 scenario finished)
 * instead of re-parsing response bodies themselves.
 */

import type {
  BenchmarkCompareResult,
  BenchmarkRunResult,
  ConflictGraphResponse,
  SimLedgerResponse,
  SimMode,
  SimStartRequest,
  SimStartResponse,
  SimTickResponse,
} from "./types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new ApiError(response.status, detail || response.statusText);
  }
  return response.json() as Promise<T>;
}

export function startSim(body: SimStartRequest = {}): Promise<SimStartResponse> {
  return request<SimStartResponse>("/sim/start", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function tickSim(simId: string): Promise<SimTickResponse> {
  return request<SimTickResponse>("/sim/tick", {
    method: "POST",
    body: JSON.stringify({ sim_id: simId }),
  });
}

export function getLedger(simId: string): Promise<SimLedgerResponse> {
  const params = new URLSearchParams({ sim_id: simId });
  return request<SimLedgerResponse>(`/sim/ledger?${params}`);
}

export function getConflictGraph(simId: string, agent: string): Promise<ConflictGraphResponse> {
  const params = new URLSearchParams({ sim_id: simId, agent });
  return request<ConflictGraphResponse>(`/conflicts/graph?${params}`);
}

export function runBenchmark(
  scenarioId: string,
  seed: number,
  nTrials: number,
  mode: SimMode,
): Promise<BenchmarkRunResult> {
  return request<BenchmarkRunResult>("/benchmark/run", {
    method: "POST",
    body: JSON.stringify({ scenario_id: scenarioId, seed, n_trials: nTrials, mode }),
  });
}

export function compareModes(
  scenarioId: string,
  seed: number,
  nTrials: number,
): Promise<BenchmarkCompareResult> {
  return request<BenchmarkCompareResult>("/benchmark/compare", {
    method: "POST",
    body: JSON.stringify({ scenario_id: scenarioId, seed, n_trials: nTrials }),
  });
}

/** Build the `/sim/stream` URL for an `EventSource` (used by `useSimStream`, Phase 10). */
export function simStreamUrl(simId: string, intervalMs = 300): string {
  const params = new URLSearchParams({ sim_id: simId, interval_ms: String(intervalMs) });
  return `${API_BASE_URL}/sim/stream?${params}`;
}
