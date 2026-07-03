interface StubViewProps {
  title: string;
  description: string;
  phase: string;
}

/** Placeholder for a view not yet wired to live data — replaced phase by phase. */
export default function StubView({ title, description, phase }: StubViewProps) {
  return (
    <div className="flex flex-col items-start gap-3 rounded-lg border border-border bg-surface-1 p-8">
      <h1 className="text-xl font-semibold text-text-primary">{title}</h1>
      <p className="max-w-xl text-sm text-text-secondary">{description}</p>
      <span className="rounded-full bg-page-plane px-3 py-1 text-xs text-text-muted">
        {phase}
      </span>
    </div>
  );
}
