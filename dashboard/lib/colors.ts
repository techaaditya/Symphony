"use client";

import { useEffect, useState } from "react";

/**
 * The same palette values as `app/globals.css`, duplicated here because
 * Leaflet/xyflow render onto canvas/SVG and need literal hex strings, not
 * CSS custom properties. Keep these two files in sync if the palette
 * changes — see `references/palette.md` in the dataviz skill for the
 * source of truth.
 */
export interface Palette {
  surface: string;
  gridline: string;
  textSecondary: string;
  textMuted: string;
  series: readonly string[];
  sequentialBlue: readonly string[];
  status: { good: string; warning: string; serious: string; critical: string };
}

const LIGHT: Palette = {
  surface: "#fcfcfb",
  gridline: "#e1e0d9",
  textSecondary: "#52514e",
  textMuted: "#898781",
  series: ["#2a78d6", "#1baf7a", "#eda100", "#008300", "#4a3aa7", "#e34948", "#e87ba4", "#eb6834"],
  sequentialBlue: ["#cde2fb", "#9ec5f4", "#5598e7", "#2a78d6", "#1c5cab", "#104281", "#0d366b"],
  status: { good: "#0ca30c", warning: "#fab219", serious: "#ec835a", critical: "#d03b3b" },
};

const DARK: Palette = {
  surface: "#1a1a19",
  gridline: "#2c2c2a",
  textSecondary: "#c3c2b7",
  textMuted: "#898781",
  series: ["#3987e5", "#199e70", "#c98500", "#008300", "#9085e9", "#e66767", "#d55181", "#d95926"],
  sequentialBlue: ["#184f95", "#256abf", "#3987e5", "#86b6ef", "#9ec5f4", "#cde2fb", "#fcfcfb"],
  status: { good: "#0ca30c", warning: "#fab219", serious: "#ec835a", critical: "#d03b3b" },
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

export function modeColor(palette: Palette, mode: string): string {
  const index = MODE_ORDER.indexOf(mode as (typeof MODE_ORDER)[number]);
  return index >= 0 ? palette.series[index] : palette.textMuted;
}

/** Maps a 0..1 fire intensity onto the sequential blue ramp (magnitude encoding). */
export function intensityColor(palette: Palette, intensity: number): string {
  const steps = palette.sequentialBlue;
  const index = Math.min(steps.length - 1, Math.max(0, Math.round(intensity * (steps.length - 1))));
  return steps[index];
}

function prefersDark(): boolean {
  return typeof window !== "undefined" && window.matchMedia("(prefers-color-scheme: dark)").matches;
}

/** Tracks `prefers-color-scheme` and returns the matching palette instance. */
export function useThemePalette(): Palette {
  const [dark, setDark] = useState(prefersDark);

  useEffect(() => {
    const query = window.matchMedia("(prefers-color-scheme: dark)");
    const listener = (event: MediaQueryListEvent) => setDark(event.matches);
    query.addEventListener("change", listener);
    return () => query.removeEventListener("change", listener);
  }, []);

  return dark ? DARK : LIGHT;
}
