/**
 * Small hand-rolled stroke icons for the five coordination departments
 * (Command Matrix, `CollaborativeGrid.tsx`) — one glyph per department
 * instead of a categorical color, so five-way identity doesn't depend on
 * hue in an otherwise near-monochrome editorial palette. No icon library
 * dependency: each is a plain inline SVG sized to `currentColor`.
 */

interface IconProps {
  className?: string;
}

export function ShieldIcon({ className }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" className={className} aria-hidden="true">
      <path
        d="M12 3l7 3v5c0 4.5-3 8.5-7 10-4-1.5-7-5.5-7-10V6l7-3z"
        stroke="currentColor"
        strokeWidth={1.5}
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function CrossIcon({ className }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" className={className} aria-hidden="true">
      <path
        d="M12 4v16M4 12h16"
        stroke="currentColor"
        strokeWidth={2}
        strokeLinecap="round"
      />
      <rect x={3.5} y={3.5} width={17} height={17} rx={4} stroke="currentColor" strokeWidth={1.5} />
    </svg>
  );
}

export function AntennaIcon({ className }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" className={className} aria-hidden="true">
      <path
        d="M12 21V10M8 6a4 4 0 018 0M5.5 3.5a8 8 0 0113 0"
        stroke="currentColor"
        strokeWidth={1.5}
        strokeLinecap="round"
      />
      <circle cx={12} cy={10} r={1.6} fill="currentColor" />
    </svg>
  );
}

export function ScaleIcon({ className }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" className={className} aria-hidden="true">
      <path
        d="M12 3v18M7 21h10M4 7l3.5-1M4 7l3.5 1M4 7v0a3 3 0 006 0M20 7l-3.5-1M20 7l-3.5 1M20 7v0a3 3 0 01-6 0M7.5 6l4.5-2 4.5 2"
        stroke="currentColor"
        strokeWidth={1.4}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function CompassIcon({ className }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" className={className} aria-hidden="true">
      <circle cx={12} cy={12} r={8.5} stroke="currentColor" strokeWidth={1.5} />
      <path d="M15 9l-2 5-4 1 2-5 4-1z" stroke="currentColor" strokeWidth={1.3} strokeLinejoin="round" />
    </svg>
  );
}

export const DEPARTMENT_ICON: Record<string, (props: IconProps) => React.ReactElement> = {
  logistics: ShieldIcon,
  medical: CrossIcon,
  comms: AntennaIcon,
  finance: ScaleIcon,
  sar: CompassIcon,
};
