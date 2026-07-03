"use client";

import { useState } from "react";
import { agentColor, useThemePalette } from "@/lib/colors";
import type { DeliberationRound, LedgerEntry, SimMode } from "@/lib/types";

interface LedgerReplayProps {
  entries: LedgerEntry[];
  mode: SimMode;
}

function isDeliberationRound(entry: LedgerEntry): entry is DeliberationRound {
  return "proposals" in entry;
}

export default function LedgerReplay({ entries, mode }: LedgerReplayProps) {
  const [index, setIndex] = useState(0);
  const palette = useThemePalette();

  if (entries.length === 0) {
    return (
      <div className="flex h-40 items-center justify-center rounded-lg border border-border bg-surface-1 text-sm text-text-muted">
        No ledger entries yet.
      </div>
    );
  }

  const entry = entries[Math.min(index, entries.length - 1)];

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center gap-3">
        <input
          type="range"
          min={0}
          max={entries.length - 1}
          value={index}
          onChange={(e) => setIndex(Number(e.target.value))}
          className="flex-1"
        />
        <span className="w-24 shrink-0 text-right text-sm text-text-secondary">
          Tick {entry.tick} / {entries[entries.length - 1].tick}
        </span>
      </div>

      {mode === "single_agent" || !isDeliberationRound(entry) ? (
        <SingleAgentDetail entry={entry} />
      ) : (
        <DeliberationDetail round={entry} palette={palette} />
      )}
    </div>
  );
}

function SingleAgentDetail({ entry }: { entry: LedgerEntry }) {
  if (isDeliberationRound(entry)) return null;
  const committed = entry.committed;
  return (
    <div className="rounded-lg border border-border bg-surface-1 p-4 text-sm">
      <h3 className="mb-2 font-semibold text-text-primary">Generalist decision</h3>
      {committed ? (
        <ul className="space-y-1 text-text-secondary">
          <li>
            <span className="text-text-muted">Action:</span> {committed.action}
          </li>
          <li>
            <span className="text-text-muted">Target resource:</span>{" "}
            {committed.target_resource ?? "—"}
          </li>
          <li>
            <span className="text-text-muted">Cost:</span> {committed.cost}
          </li>
          <li>
            <span className="text-text-muted">Served:</span>{" "}
            {committed.served === null ? "unjudged" : committed.served ? "yes" : "wasted"}
          </li>
        </ul>
      ) : (
        <p className="text-text-muted">No action taken this tick.</p>
      )}
    </div>
  );
}

function DeliberationDetail({
  round,
  palette,
}: {
  round: DeliberationRound;
  palette: ReturnType<typeof useThemePalette>;
}) {
  const conflictedResources = Object.keys(round.conflicts);

  return (
    <div className="flex flex-col gap-4">
      <Section title="Proposals">
        <ul className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          {round.proposals.map((p) => (
            <li
              key={p.agent}
              className="rounded-md border border-border bg-surface-1 p-3 text-sm"
              style={{ borderLeftColor: agentColor(palette, p.agent), borderLeftWidth: 3 }}
            >
              <p className="font-medium capitalize text-text-primary">
                {p.agent}
                {p.veto && (
                  <span className="ml-2 rounded-full bg-status-critical/10 px-2 py-0.5 text-xs text-status-critical">
                    veto: {p.veto_target}
                  </span>
                )}
              </p>
              <p className="text-text-secondary">
                {p.action} {p.target_resource ? `→ ${p.target_resource}` : ""}
              </p>
              <p className="mt-1 text-xs text-text-muted">{p.rationale}</p>
              <p className="mt-1 text-xs text-text-muted">
                confidence {p.confidence.toFixed(2)}
                {p.cost ? ` · cost ${p.cost}` : ""}
              </p>
            </li>
          ))}
        </ul>
      </Section>

      {conflictedResources.length > 0 && (
        <Section title={`Conflicts (${conflictedResources.length})`}>
          <ul className="space-y-1 text-sm text-text-secondary">
            {conflictedResources.map((resource) => (
              <li key={resource}>
                <span className="font-medium text-text-primary">{resource}</span>:{" "}
                {round.conflicts[resource].map((p) => p.agent).join(" vs. ")}
              </li>
            ))}
          </ul>
        </Section>
      )}

      {round.debate_log.length > 0 && (
        <Section title="Debate transcript">
          <ul className="space-y-2 text-sm">
            {round.debate_log.map((entry, i) => (
              <li key={i} className="rounded-md border border-border bg-surface-1 p-3">
                <p className="text-xs text-text-muted">
                  {entry.resource} · round {entry.round}
                </p>
                <p className="font-medium capitalize text-text-primary">{entry.agent}</p>
                <p className="text-text-secondary">{entry.rebuttal}</p>
                <p className="mt-1 text-xs text-text-muted">
                  scored by:{" "}
                  {Object.entries(entry.scores)
                    .map(([voter, score]) => `${voter} ${score.toFixed(2)}`)
                    .join(", ")}
                </p>
              </li>
            ))}
          </ul>
        </Section>
      )}

      {Object.keys(round.votes).length > 0 && (
        <Section title="Votes">
          <ul className="space-y-1 text-sm text-text-secondary">
            {Object.entries(round.votes).map(([resource, tally]) => (
              <li key={resource}>
                <span className="font-medium text-text-primary">{resource}</span>:{" "}
                {Object.entries(tally)
                  .sort((a, b) => b[1] - a[1])
                  .map(([agent, score]) => `${agent} ${score.toFixed(2)}`)
                  .join(", ")}
                {round.escalated && (
                  <span className="ml-2 rounded-full bg-status-warning/10 px-2 py-0.5 text-xs text-status-warning">
                    escalated
                  </span>
                )}
              </li>
            ))}
          </ul>
        </Section>
      )}

      <Section title="Outcome">
        <div className="flex flex-col gap-2 text-sm">
          {round.outcome.committed.length > 0 && (
            <div>
              <p className="text-text-muted">Committed</p>
              <ul className="text-text-secondary">
                {round.outcome.committed.map((c, i) => (
                  <li key={i}>
                    <span className="text-status-good">✓</span> {c.agent} — {c.action} (
                    {c.target_resource ?? "no resource"})
                  </li>
                ))}
              </ul>
            </div>
          )}
          {round.outcome.vetoed.length > 0 && (
            <div>
              <p className="text-text-muted">Vetoed</p>
              <ul className="text-text-secondary">
                {round.outcome.vetoed.map((v, i) => (
                  <li key={i}>
                    <span className="text-status-critical">✕</span> {v.agent} —{" "}
                    {v.target_resource} ({v.reason})
                  </li>
                ))}
              </ul>
            </div>
          )}
          {round.outcome.coordinator_rulings?.map((r, i) => (
            <p key={i} className="text-text-secondary">
              Coordinator ruled <span className="font-medium">{r.ruling}</span> wins {r.resource}
            </p>
          ))}
        </div>
      </Section>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h3 className="mb-2 text-sm font-semibold text-text-primary">{title}</h3>
      {children}
    </div>
  );
}
