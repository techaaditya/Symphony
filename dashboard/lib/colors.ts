"use client";

/**
 * The same exact Color Hunt palette as `app/globals.css`, duplicated here
 * because Leaflet/xyflow render onto canvas/SVG and need literal color
 * strings, not CSS custom properties. Keep these two files in sync if the
 * palette changes. Single fixed light theme -- no dark-mode variant, so
 * `useThemePalette` is a plain accessor kept only so call sites don't need
 * to change if a theme ever comes back.
 */
export interface Palette {
  surface: string;
  gridline: string;
  textPrimary: string;
  textSecondary: string;
  textMuted: string;
  series: readonly string[];
  sequentialFire: readonly string[];
  status: { good: string; warning: string; serious: string; critical: string };
}

const LIGHT: Palette = {
  surface: "#ead8c0",
  gridline: "#d1bb9e",
  textPrimary: "#3e2d1c",
  textSecondary: "rgba(62, 45, 28, 0.72)",
  textMuted: "rgba(62, 45, 28, 0.52)",
  // Espresso/rust/olive/ochre/tan -- a categorical distinction the four core
  // palette roles don't cover, derived within the same warm family for the
  // Conflict Graph Explorer and ledger proposal borders. Ochre/tan are
  // darkened a step past their first-pass values so the off-white text used
  // on a *focused* node (ConflictGraph.tsx) clears 4.5:1 contrast -- the
  // lighter originals measured 3.8:1 and 4.4:1, both too low for 11px text.
  series: ["#3e2d1c", "#9c4a2c", "#71713a", "#8a6023", "#7a5f3f"],
  sequentialFire: ["#fff2e1", "#ead8c0", "#d1bb9e", "#a79277", "#8a6f4e", "#5c4630", "#3e2d1c"],
  status: { good: "#6b7a3a", warning: "#c98a2c", serious: "#b5622b", critical: "#8c3b2e" },
};

/** Fixed agent -> categorical-slot order, so a given agent always draws in the same hue. */
export const AGENT_ORDER = ["logistics", "medical", "comms", "finance", "sar"] as const;

export function agentColor(palette: Palette, agent: string): string {
  const index = AGENT_ORDER.indexOf(agent as (typeof AGENT_ORDER)[number]);
  return index >= 0 ? palette.series[index] : palette.textMuted;
}

/** Fixed benchmark-mode -> categorical-slot order, independent of AGENT_ORDER's
 * slot assignment (a different chart, a different identity dimension). */
export const MODE_ORDER = ["single_agent", "society"] as const;

/** Exact palette roles per the spec: Muted Brown for the five-agent society
 * (the primary accent), Warm Sand for the single-agent baseline -- not
 * reused from the agent `series` array, since that's a different chart. */
const MODE_HEX: Record<(typeof MODE_ORDER)[number], string> = {
  single_agent: "#d1bb9e",
  society: "#a79277",
};

export function modeColor(_palette: Palette, mode: string): string {
  return MODE_HEX[mode as (typeof MODE_ORDER)[number]] ?? _palette.textMuted;
}

/** Maps a 0..1 fire intensity onto the sequential linen-to-espresso ramp (magnitude encoding). */
export function intensityColor(palette: Palette, intensity: number): string {
  const steps = palette.sequentialFire;
  const index = Math.min(steps.length - 1, Math.max(0, Math.round(intensity * (steps.length - 1))));
  return steps[index];
}

/** No dark-mode variant -- always the one warm-light palette. */
export function useThemePalette(): Palette {
  return LIGHT;
}
