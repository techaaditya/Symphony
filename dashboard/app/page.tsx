const VIEWS = [
  {
    href: "/live",
    title: "Live",
    description: "Disaster map and agent graph, driven by /sim/stream.",
  },
  {
    href: "/ledger",
    title: "Ledger",
    description: "Replay every deliberation round: proposals, debate, votes, escalations, vetoes.",
  },
  {
    href: "/conflicts",
    title: "Conflicts",
    description: "Explore the Conflict Graph — every clash between two agents over a resource.",
  },
  {
    href: "/benchmark",
    title: "Benchmark",
    description: "Society vs. single-agent baseline, with the token-cost tradeoff made explicit.",
  },
];

export default function Home() {
  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-text-primary">
          Symphony — Agent Society
        </h1>
        <p className="mt-2 max-w-2xl text-sm text-text-secondary">
          Five specialist agents — Logistics, Medical, Comms, Finance, Search &amp; Rescue — and a
          Coordinator negotiate scarce disaster-response resources through the Parliament Protocol
          (propose → debate → vote → escalate → commit).{" "}
          <span className="text-text-primary">
            Agents propose, deterministic code adjudicates.
          </span>
        </p>
      </div>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {VIEWS.map((view) => (
          <a
            key={view.href}
            href={view.href}
            className="rounded-lg border border-border bg-surface-1 p-5 transition-colors hover:border-text-muted"
          >
            <h2 className="text-sm font-semibold text-text-primary">{view.title}</h2>
            <p className="mt-1 text-sm text-text-secondary">{view.description}</p>
          </a>
        ))}
      </div>
    </div>
  );
}
