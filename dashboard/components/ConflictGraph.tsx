"use client";

import "@xyflow/react/dist/style.css";
import { Background, ReactFlow, type Edge, type Node } from "@xyflow/react";
import { agentColor, useThemePalette } from "@/lib/colors";
import type { ConflictGraphResponse } from "@/lib/types";

interface ConflictGraphProps {
  graph: ConflictGraphResponse | null;
  focusAgent: string;
}

const ROW_HEIGHT = 90;
const COL_WIDTH = 130;

function outcomeColor(outcome: string, focusAgent: string, palette: ReturnType<typeof useThemePalette>) {
  if (outcome === "vetoed") return palette.status.critical;
  if (outcome === "unresolved") return palette.status.warning;
  return outcome === focusAgent ? palette.status.good : palette.textMuted;
}

export default function ConflictGraph({ graph, focusAgent }: ConflictGraphProps) {
  const palette = useThemePalette();

  if (!graph || graph.proposals.length === 0) {
    return (
      <div className="flex h-[480px] items-center justify-center rounded-lg border border-border bg-surface-1 text-sm text-text-muted">
        No recorded conflicts for this agent yet.
      </div>
    );
  }

  const ticks = Array.from(new Set(graph.proposals.map((p) => p.tick))).sort((a, b) => a - b);
  const tickIndex = new Map(ticks.map((t, i) => [t, i]));
  const agentNames = Array.from(new Set(graph.agents.map((a) => a.name)));
  const rowIndex = new Map(agentNames.map((name, i) => [name, i]));

  const nodes: Node[] = graph.proposals.map((proposal) => {
    const color = agentColor(palette, proposal.agent);
    return {
      id: proposal.id,
      position: {
        x: (tickIndex.get(proposal.tick) ?? 0) * COL_WIDTH,
        y: (rowIndex.get(proposal.agent) ?? 0) * ROW_HEIGHT,
      },
      data: { label: `${proposal.agent} · t${proposal.tick}` },
      style: {
        background: proposal.agent === focusAgent ? color : palette.surface,
        color: proposal.agent === focusAgent ? "#ffffff" : palette.textSecondary,
        border: `2px solid ${color}`,
        borderRadius: 8,
        fontSize: 11,
        width: 110,
        textTransform: "capitalize",
      },
    };
  });

  const edges: Edge[] = graph.edges.map((edge, i) => {
    const color = outcomeColor(edge.outcome, focusAgent, palette);
    return {
      id: `${edge.source}-${edge.target}-${i}`,
      source: edge.source,
      target: edge.target,
      label: `${edge.resource} · ${edge.outcome}`,
      animated: edge.outcome === "unresolved",
      style: { stroke: color, strokeWidth: 2 },
      labelStyle: { fill: palette.textSecondary, fontSize: 10 },
    };
  });

  return (
    <div className="h-[480px] overflow-hidden rounded-lg border border-border bg-surface-1">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={false}
        fitView
        proOptions={{ hideAttribution: true }}
      >
        <Background color={palette.gridline} gap={24} />
      </ReactFlow>
    </div>
  );
}
