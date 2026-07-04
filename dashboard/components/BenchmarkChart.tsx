"use client";

import { MODE_ORDER, modeColor, useThemePalette } from "@/lib/colors";
import type { BenchmarkCompareResult, BenchmarkRunResult, SimMode } from "@/lib/types";

interface BenchmarkChartProps {
  result: BenchmarkCompareResult;
}

interface MetricConfig {
  key: "objectives_met_pct" | "resource_waste_pct" | "time_to_allocate_s" | "token_cost";
  label: string;
  formatValue: (v: number) => string;
}

const METRICS: MetricConfig[] = [
  { key: "objectives_met_pct", label: "Objectives met", formatValue: (v) => `${v.toFixed(1)}%` },
  { key: "resource_waste_pct", label: "Resource waste", formatValue: (v) => `${v.toFixed(1)}%` },
  { key: "time_to_allocate_s", label: "Time to allocate", formatValue: (v) => `${v.toFixed(2)}s` },
  {
    key: "token_cost",
    label: "Token cost",
    formatValue: (v) => new Intl.NumberFormat("en", { notation: "compact" }).format(v),
  },
];

const MODE_LABEL: Record<SimMode, string> = {
  single_agent: "Single-agent baseline",
  society: "Five-agent society",
};

export default function BenchmarkChart({ result }: BenchmarkChartProps) {
  const palette = useThemePalette();

  const tokenSingle = result.single_agent.token_cost.mean;
  const tokenSociety = result.society.token_cost.mean;
  const tokenDeltaPct = tokenSingle > 0 ? ((tokenSociety - tokenSingle) / tokenSingle) * 100 : 0;
  const objectivesDelta =
    result.society.objectives_met_pct.mean - result.single_agent.objectives_met_pct.mean;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center gap-4">
        {MODE_ORDER.map((mode) => (
          <span key={mode} className="flex items-center gap-1.5 text-sm text-text-secondary">
            <span className="h-2.5 w-2.5 rounded-full" style={{ background: modeColor(palette, mode) }} />
            {MODE_LABEL[mode]}
          </span>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
        {METRICS.map((metric) => (
          <MetricPanel key={metric.key} metric={metric} result={result} palette={palette} />
        ))}
      </div>

      <div className="rounded-lg border border-border bg-surface-1 p-4">
        <h3 className="mb-1 text-sm font-semibold text-text-primary">Token-cost tradeoff</h3>
        <p className="text-sm text-text-secondary">
          The five-agent society spends{" "}
          <span
            className="font-medium"
            style={{ color: tokenDeltaPct > 0 ? palette.status.warning : palette.status.good }}
          >
            {tokenDeltaPct >= 0 ? "+" : ""}
            {tokenDeltaPct.toFixed(0)}%
          </span>{" "}
          tokens versus the single-agent baseline ({new Intl.NumberFormat("en", { notation: "compact" }).format(tokenSociety)} vs{" "}
          {new Intl.NumberFormat("en", { notation: "compact" }).format(tokenSingle)} mean per run), for{" "}
          <span
            className="font-medium"
            style={{ color: objectivesDelta >= 0 ? palette.status.good : palette.status.critical }}
          >
            {objectivesDelta >= 0 ? "+" : ""}
            {objectivesDelta.toFixed(1)} pp
          </span>{" "}
          objectives met. Deliberation costs more tokens per tick; whether that trade is worth it
          depends on how much a missed objective costs in the real scenario.
        </p>
      </div>
    </div>
  );
}

function MetricPanel({
  metric,
  result,
  palette,
}: {
  metric: MetricConfig;
  result: Record<SimMode, BenchmarkRunResult>;
  palette: ReturnType<typeof useThemePalette>;
}) {
  const width = 260;
  const height = 200;
  const baselineY = height - 30;
  const barWidth = 40;
  const centers = [width / 2 - 55, width / 2 + 55];

  const summaries = MODE_ORDER.map((mode) => result[mode][metric.key]);
  const maxValue = Math.max(...summaries.map((s) => s.mean + s.sd), 0.0001);
  const scale = (v: number) => (v / maxValue) * (baselineY - 20);

  return (
    <div className="rounded-lg border border-border bg-surface-1 p-4">
      <h3 className="mb-2 text-sm font-medium text-text-secondary">{metric.label}</h3>
      <svg width={width} height={height} role="img" aria-label={`${metric.label} comparison chart`}>
        <line x1={10} y1={baselineY} x2={width - 10} y2={baselineY} stroke={palette.gridline} strokeWidth={1} />
        {MODE_ORDER.map((mode, i) => {
          const summary = result[mode][metric.key];
          const barHeight = scale(summary.mean);
          const color = modeColor(palette, mode);
          const cx = centers[i];
          const errTop = baselineY - scale(summary.mean + summary.sd);
          const errBottom = baselineY - scale(Math.max(0, summary.mean - summary.sd));

          return (
            <g key={mode}>
              <rect
                x={cx - barWidth / 2}
                y={baselineY - barHeight}
                width={barWidth}
                height={barHeight}
                rx={4}
                fill={color}
              />
              {summary.sd > 0 && (
                <>
                  <line x1={cx} y1={errTop} x2={cx} y2={errBottom} stroke={palette.textMuted} strokeWidth={1.5} />
                  <line x1={cx - 6} y1={errTop} x2={cx + 6} y2={errTop} stroke={palette.textMuted} strokeWidth={1.5} />
                  <line x1={cx - 6} y1={errBottom} x2={cx + 6} y2={errBottom} stroke={palette.textMuted} strokeWidth={1.5} />
                </>
              )}
              <text
                x={cx}
                y={Math.min(baselineY - barHeight, errTop) - 8}
                textAnchor="middle"
                fontSize={11}
                fill={palette.textSecondary}
              >
                {metric.formatValue(summary.mean)}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
