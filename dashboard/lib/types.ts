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

export interface WorldStatePayload {
  tick: number;
  zones: Record<string, Zone>;
  resources: ResourcePools;
  towers: Record<string, Tower>;
  casualties: CasualtyReport[];
  trapped: TrappedReport[];
}

export interface DebateLogEntry {
  resource: string;
  round: number;
  agent: string;
  rebuttal: string;
  scores: Record<string, number>;
}

export interface CommittedAction {
  agent: string;
  action: string;
  target_resource: string | null;
  cost: number;
  served: boolean | null;
}

export interface VetoedAction {
  agent: string;
  target_resource: string;
  reason: string;
}

export interface CoordinatorRuling {
  resource: string;
  ruling: string;
  [key: string]: unknown;
}

export interface RoundOutcome {
  committed: CommittedAction[];
  vetoed: VetoedAction[];
  coordinator_rulings?: CoordinatorRuling[];
}

/** One Parliament Protocol round, the shape written to the JSONL ledger
 * (`symphony/ledger/store.py`) -- no `world_state`, since that's a live-view
 * concern, not part of the deliberation record itself. */
export interface DeliberationRound {
  tick: number;
  proposals: Proposal[];
  conflicts: Record<string, Proposal[]>;
  debate_log: DebateLogEntry[];
  votes: Record<string, Record<string, number>>;
  outcome: RoundOutcome;
  escalated: boolean;
}

export interface RoundResultPayload extends DeliberationRound {
  world_state: WorldStatePayload;
}

export interface SingleAgentLedgerEntry {
  tick: number;
  committed: CommittedAction | null;
}

export interface SingleAgentTickPayload extends SingleAgentLedgerEntry {
  world_state: WorldStatePayload;
}

export type TickResultPayload = RoundResultPayload | SingleAgentTickPayload;
export type LedgerEntry = DeliberationRound | SingleAgentLedgerEntry;

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
  entries: LedgerEntry[];
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
