"use client";

import { DEPARTMENT_ICON } from "@/components/icons";
import { AGENT_ORDER } from "@/lib/colors";
import type { Proposal, RoundResultPayload, SingleAgentTickPayload } from "@/lib/types";

interface CollaborativeGridProps {
  latest: RoundResultPayload | SingleAgentTickPayload | null;
}

const DEPARTMENT_LABEL: Record<string, string> = {
  logistics: "Logistics",
  medical: "Medical",
  comms: "Comms",
  finance: "Finance",
  sar: "Search & Rescue",
};

function isRoundResult(
  latest: RoundResultPayload | SingleAgentTickPayload,
): latest is RoundResultPayload {
  return "proposals" in latest;
}

type TransactionStatus = "committed" | "escalated" | "vetoed" | "proposed";

function statusLabel(status: TransactionStatus): string {
  switch (status) {
    case "committed":
      return "Committed";
    case "escalated":
      return "Escalated";
    case "vetoed":
      return "Vetoed";
    default:
      return "Proposed";
  }
}

// Muted pills, not high-contrast badges: every pill keeps the same espresso
// text and a soft tinted background, with only a small colored dot carrying
// the status distinction -- scannable without reintroducing saturated,
// dev-tool-style colored text.
function statusBg(status: TransactionStatus): string {
  switch (status) {
    case "vetoed":
      return "bg-status-critical/10";
    case "escalated":
      return "bg-status-warning/10";
    case "committed":
      return "bg-status-good/10";
    default:
      return "bg-surface-2";
  }
}

function statusDot(status: TransactionStatus): string {
  switch (status) {
    case "vetoed":
      return "bg-status-critical";
    case "escalated":
      return "bg-status-warning";
    case "committed":
      return "bg-status-good";
    default:
      return "bg-text-muted";
  }
}

/**
 * Command Matrix: the five coordination departments as a fixed grid of
 * cards, identified by icon rather than color (a near-monochrome editorial
 * palette can't carry five-way hue distinction the way a dev-tool palette
 * could). Cross-department activity renders as a structured "Active
 * Transactions" table instead of animated lines over a node graph.
 */
export default function CollaborativeGrid({ latest }: CollaborativeGridProps) {
  if (!latest) {
    return (
      <div className="card-panel flex h-[480px] flex-col items-center justify-center gap-2 rounded-lg text-sm text-text-muted">
        Start a simulation to see departments coordinate.
      </div>
    );
  }

  if (!isRoundResult(latest)) {
    const committed = latest.committed;
    return (
      <div className="card-panel flex h-[480px] flex-col items-center justify-center gap-2 rounded-lg p-6 text-center text-sm text-text-muted">
        <p className="font-medium text-text-primary">Single generalist agent</p>
        <p>{committed ? `Decision: ${committed.action}` : "Holding — no action taken this tick."}</p>
      </div>
    );
  }

  const round = latest;
  const proposalByAgent = new Map<string, Proposal>(round.proposals.map((p) => [p.agent, p]));
  const conflictedResourceByAgent = new Map<string, string>();
  for (const [resource, proposals] of Object.entries(round.conflicts)) {
    for (const p of proposals) conflictedResourceByAgent.set(p.agent, resource);
  }
  const vetoedAgents = new Set(round.outcome.vetoed.map((v) => v.agent));
  const committedAgents = new Set(round.outcome.committed.map((c) => c.agent));

  function statusFor(agent: string): TransactionStatus {
    if (vetoedAgents.has(agent)) return "vetoed";
    if (conflictedResourceByAgent.has(agent) && round.escalated) return "escalated";
    if (committedAgents.has(agent)) return "committed";
    return "proposed";
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        {AGENT_ORDER.map((agent) => {
          const Icon = DEPARTMENT_ICON[agent];
          const proposal = proposalByAgent.get(agent);
          const conflicted = conflictedResourceByAgent.has(agent);
          const vetoed = vetoedAgents.has(agent);
          return (
            <div
              key={agent}
              className={`flex flex-col items-center gap-2 rounded-lg border p-4 text-center transition-all duration-200 ${
                vetoed
                  ? "border-status-critical bg-status-critical/5"
                  : conflicted
                    ? "border-text-secondary bg-surface-2"
                    : "border-border bg-surface-2"
              }`}
            >
              <Icon className="h-7 w-7 text-text-primary" />
              <span className="text-sm font-medium text-text-primary">
                {DEPARTMENT_LABEL[agent]}
              </span>
              {proposal ? (
                <span className="text-xs text-text-secondary">
                  {conflicted ? `Contesting ${conflictedResourceByAgent.get(agent)}` : "Standing by"}
                </span>
              ) : (
                <span className="text-xs text-text-muted">No proposal</span>
              )}
            </div>
          );
        })}
      </div>

      <div className="card-panel overflow-hidden rounded-lg">
        <div className="border-b border-border bg-surface-2 px-4 py-2.5">
          <h3 className="text-sm font-semibold text-text-primary">
            Active Transactions — Tick {latest.tick}
          </h3>
        </div>
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-border text-xs uppercase tracking-wide text-text-muted">
              <th className="px-4 py-2 font-medium">Department</th>
              <th className="px-4 py-2 font-medium">Action</th>
              <th className="px-4 py-2 font-medium">Resource</th>
              <th className="px-4 py-2 font-medium">Status</th>
            </tr>
          </thead>
          <tbody>
            {AGENT_ORDER.filter((agent) => proposalByAgent.has(agent)).map((agent, i) => {
              const proposal = proposalByAgent.get(agent)!;
              const status = statusFor(agent);
              return (
                <tr
                  key={agent}
                  className={`border-b border-border last:border-b-0 ${
                    i % 2 === 1 ? "bg-page-plane" : "bg-surface-1"
                  }`}
                >
                  <td className="px-4 py-2.5 font-medium text-text-primary">
                    {DEPARTMENT_LABEL[agent]}
                  </td>
                  <td className="px-4 py-2.5 text-text-secondary">{proposal.action}</td>
                  <td className="px-4 py-2.5 text-text-secondary">
                    {proposal.target_resource ?? "—"}
                  </td>
                  <td className="px-4 py-2.5">
                    <span
                      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium text-text-primary ${statusBg(status)}`}
                    >
                      <span className={`h-1.5 w-1.5 rounded-full ${statusDot(status)}`} />
                      {statusLabel(status)}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
