"use client";

import "@xyflow/react/dist/style.css";
import { Background, ReactFlow, type Edge, type Node } from "@xyflow/react";
import { AGENT_ORDER, agentColor, useThemePalette } from "@/lib/colors";
import type { RoundResultPayload, SingleAgentTickPayload } from "@/lib/types";

interface AgentGraphProps {
  latest: RoundResultPayload | SingleAgentTickPayload | null;
}

const CENTER = { x: 260, y: 200 };
const RADIUS = 170;

function isRoundResult(
  latest: RoundResultPayload | SingleAgentTickPayload,
): latest is RoundResultPayload {
  return "proposals" in latest;
}

export default function AgentGraph({ latest }: AgentGraphProps) {
  const palette = useThemePalette();

  if (!latest || !isRoundResult(latest)) {
    return (
      <div className="flex h-[480px] flex-col items-center justify-center gap-2 rounded-lg border border-border bg-surface-1 text-sm text-text-muted">
        {latest
          ? `Generalist decision: ${JSON.stringify(latest.committed?.action ?? "hold")}`
          : "Start a simulation to see agents deliberate."}
      </div>
    );
  }

  const proposingAgents = new Set(latest.proposals.map((p) => p.agent));
  const conflictedResourceByAgent = new Map<string, string>();
  for (const [resource, proposals] of Object.entries(latest.conflicts)) {
    for (const p of proposals) conflictedResourceByAgent.set(p.agent, resource);
  }

  const coordinatorNode: Node = {
    id: "coordinator",
    position: { x: CENTER.x, y: CENTER.y },
    data: { label: "Coordinator" },
    style: {
      background: palette.surface,
      color: palette.textSecondary,
      border: `2px solid ${palette.gridline}`,
      borderRadius: 9999,
      width: 110,
      height: 110,
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      fontSize: 13,
      fontWeight: 600,
    },
  };

  const agentNodes: Node[] = AGENT_ORDER.map((agent, i) => {
    const angle = (2 * Math.PI * i) / AGENT_ORDER.length - Math.PI / 2;
    const active = proposingAgents.has(agent);
    const color = agentColor(palette, agent);
    return {
      id: agent,
      position: {
        x: CENTER.x + RADIUS * Math.cos(angle) - 45,
        y: CENTER.y + RADIUS * Math.sin(angle) - 45,
      },
      data: { label: agent },
      style: {
        background: active ? color : palette.surface,
        color: active ? "#ffffff" : palette.textMuted,
        border: `2px solid ${color}`,
        borderRadius: 9999,
        width: 90,
        height: 90,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontSize: 12,
        fontWeight: 600,
        textTransform: "capitalize",
        transition: "background 200ms",
      },
    };
  });

  const edges: Edge[] = AGENT_ORDER.filter((agent) => proposingAgents.has(agent)).map((agent) => {
    const conflicted = conflictedResourceByAgent.has(agent);
    const proposal = latest.proposals.find((p) => p.agent === agent);
    const color = proposal?.veto ? palette.status.critical : agentColor(palette, agent);
    return {
      id: `${agent}-coordinator`,
      source: agent,
      target: "coordinator",
      animated: conflicted,
      label: conflicted ? `⚡ ${conflictedResourceByAgent.get(agent)}` : proposal?.target_resource,
      style: { stroke: color, strokeWidth: conflicted ? 2.5 : 1.5 },
      labelStyle: { fill: palette.textSecondary, fontSize: 11 },
    };
  });

  return (
    <div className="h-[480px] overflow-hidden rounded-lg border border-border bg-surface-1">
      <ReactFlow
        nodes={[coordinatorNode, ...agentNodes]}
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
