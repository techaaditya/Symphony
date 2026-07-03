/**
 * Types mirroring `symphony/api/schemas.py` and `symphony/models.py`.
 * Kept as plain interfaces (not generated) since the API surface is small
 * and stable; if it grows, generate this from the FastAPI OpenAPI schema
 * instead of hand-maintaining it.
 */

export type SimMode = "society" | "single_agent";

export interface Proposal {
  agent: string;
  action: string;
  target_resource: string | null;
  rationale: string;
  confidence: number;
  veto: boolean;
  veto_target: string | null;
  cost: number;
}

export interface RoundResultPayload {
  tick: number;
  proposals: Proposal[];
  conflicts: Record<string, Proposal[]>;
  debate_log: Record<string, unknown>[];
  votes: Record<string, Record<string, number>>;
  outcome: Record<string, unknown>;
  escalated: boolean;
}

export interface SingleAgentTickPayload {
  tick: number;
  committed: Record<string, unknown> | null;
}

export type TickResultPayload = RoundResultPayload | SingleAgentTickPayload;

export interface SimStartRequest {
  scenario_id?: string;
  seed?: number;
  mode?: SimMode;
}

export interface SimStartResponse {
  sim_id: string;
  scenario_id: string;
  seed: number;
  mode: SimMode;
  ticks_total: number;
}

export interface SimTickResponse {
  sim_id: string;
  tick: number;
  finished: boolean;
  result: TickResultPayload;
}

export interface SimLedgerResponse {
  sim_id: string;
  mode: SimMode;
  entries: Record<string, unknown>[];
}

export interface MetricSummary {
  mean: number;
  sd: number;
}

export interface BenchmarkRunResult {
  mode: SimMode;
  scenario_id: string;
  n_trials: number;
  objectives_met_pct: MetricSummary;
  time_to_allocate_s: MetricSummary;
  resource_waste_pct: MetricSummary;
  token_cost: MetricSummary;
}

export interface BenchmarkCompareResult {
  single_agent: BenchmarkRunResult;
  society: BenchmarkRunResult;
}

export interface ConflictGraphAgent {
  name: string;
}

export interface ConflictGraphProposal {
  id: string;
  agent: string;
  tick: number;
  rationale: string;
}

export interface ConflictGraphEdge {
  source: string;
  target: string;
  resource: string;
  outcome: string;
  tick: number;
}

export interface ConflictGraphResponse {
  agents: ConflictGraphAgent[];
  proposals: ConflictGraphProposal[];
  edges: ConflictGraphEdge[];
}

// -- blackboard world-state schema (symphony/models.py), for the map/graph views --

export interface Zone {
  id: string;
  name: string;
  lat: number;
  lng: number;
  population: number;
  fire_intensity: number;
  road_status: "open" | "closed";
}

export interface ResourcePools {
  helicopters: number;
  medic_teams: number;
  sar_teams: number;
  comms_towers: number;
  budget_remaining: number;
}

export interface Tower {
  id: string;
  zone_id: string;
  operational: boolean;
}

export interface CasualtyReport {
  zone_id: string;
  count: number;
  severity: "minor" | "serious" | "critical";
  tick_reported: number;
  treated: boolean;
}

export interface TrappedReport {
  zone_id: string;
  count: number;
  tick_reported: number;
  window_ends_tick: number;
  rescued: boolean;
}
