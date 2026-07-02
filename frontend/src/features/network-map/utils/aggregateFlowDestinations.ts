import { NetworkMapEdge, NetworkMapNode } from '../types/networkMap';
import { globalPortNodeId } from './flowLabels';
import { edgeKey } from './whatIfSimulation';

export type PortDestExpansion = 'summary' | 'partial' | 'full';

export const FLOW_DEST_TOP_N = 5;

export interface FlowDestinationAggregateMeta {
  /** Original flow node ids grouped by port number. */
  flowsByPort: Map<number, string[]>;
  expansionByPort: Record<number, PortDestExpansion>;
}

export interface AggregatedFlowGraph {
  nodes: NetworkMapNode[];
  edges: NetworkMapEdge[];
  meta: FlowDestinationAggregateMeta;
}

function summaryNodeId(port: number): string {
  return `flow_summary:${port}`;
}

function moreNodeId(port: number): string {
  return `flow_more:${port}`;
}

function portFromNodeId(nodeId: string): number | null {
  const match = nodeId.match(/^flow_(?:summary|more):(\d+)$/);
  if (!match) {
    return null;
  }
  const port = Number(match[1]);
  return Number.isFinite(port) ? port : null;
}

function defaultExpansion(flowCount: number): PortDestExpansion {
  if (flowCount <= FLOW_DEST_TOP_N) {
    return 'full';
  }
  return 'summary';
}

function resolveExpansion(port: number, flowCount: number, overrides: Record<number, PortDestExpansion>): PortDestExpansion {
  const chosen = overrides[port] ?? defaultExpansion(flowCount);
  if (flowCount <= FLOW_DEST_TOP_N) {
    return 'full';
  }
  return chosen;
}

function flowsForPort(edges: NetworkMapEdge[], portId: string, flowNodes: Map<string, NetworkMapNode>): NetworkMapNode[] {
  const ids = edges.filter((e) => e.kind === 'port_to_flow' && e.source === portId).map((e) => e.target);
  return ids
    .map((id) => flowNodes.get(id))
    .filter((node): node is NetworkMapNode => node != null)
    .sort((a, b) => a.label.localeCompare(b.label));
}

/** Collapse per-port destination flows into summary / top-N / full views. */
export function aggregateFlowDestinations(
  nodes: NetworkMapNode[],
  edges: NetworkMapEdge[],
  expansionByPort: Record<number, PortDestExpansion> = {},
): AggregatedFlowGraph {
  const flowNodes = new Map(nodes.filter((n) => n.type === 'flow').map((n) => [n.id, n]));
  const portNodes = nodes.filter((n) => n.type === 'port');
  const hiddenFlowIds = new Set<string>();

  if (portNodes.length === 0 || flowNodes.size === 0) {
    return {
      nodes,
      edges,
      meta: { flowsByPort: new Map(), expansionByPort: {} },
    };
  }

  const flowsByPort = new Map<number, string[]>();
  const effectiveExpansion: Record<number, PortDestExpansion> = {};

  for (const portNode of portNodes) {
    const portNum = Number(portNode.label);
    if (!Number.isFinite(portNum)) {
      continue;
    }
    const flows = flowsForPort(edges, portNode.id, flowNodes);
    flowsByPort.set(
      portNum,
      flows.map((f) => f.id),
    );
    effectiveExpansion[portNum] = resolveExpansion(portNum, flows.length, expansionByPort);
  }

  const keepFlowIds = new Set<string>();
  const syntheticNodes: NetworkMapNode[] = [];
  const syntheticEdges: NetworkMapEdge[] = [];

  for (const portNode of portNodes) {
    const portNum = Number(portNode.label);
    if (!Number.isFinite(portNum)) {
      continue;
    }
    const flows = flowsForPort(edges, portNode.id, flowNodes);
    const expansion = effectiveExpansion[portNum];
    const count = flows.length;
    if (count === 0) {
      continue;
    }

    if (expansion === 'summary') {
      for (const flow of flows) {
        hiddenFlowIds.add(flow.id);
      }
      syntheticNodes.push({
        id: summaryNodeId(portNum),
        type: 'flow_summary',
        label: `${count} connection${count === 1 ? '' : 's'} on ${portNum}`,
      });
      syntheticEdges.push({
        source: portNode.id,
        target: summaryNodeId(portNum),
        kind: 'port_to_flow',
        query_count: count,
        blocked_count: 0,
      });
      continue;
    }

    if (expansion === 'partial') {
      const visible = flows.slice(0, FLOW_DEST_TOP_N);
      const rest = flows.slice(FLOW_DEST_TOP_N);
      for (const flow of visible) {
        keepFlowIds.add(flow.id);
      }
      for (const flow of rest) {
        hiddenFlowIds.add(flow.id);
      }
      if (rest.length > 0) {
        syntheticNodes.push({
          id: moreNodeId(portNum),
          type: 'flow_more',
          label: `+${rest.length} more`,
        });
        syntheticEdges.push({
          source: portNode.id,
          target: moreNodeId(portNum),
          kind: 'port_to_flow',
          query_count: rest.length,
          blocked_count: 0,
        });
      }
      continue;
    }

    for (const flow of flows) {
      keepFlowIds.add(flow.id);
    }
  }

  const outNodes = [
    ...nodes.filter((n) => n.type !== 'flow' || keepFlowIds.has(n.id)),
    ...syntheticNodes,
  ];

  const outEdges = [
    ...edges.filter((e) => {
      if (e.kind !== 'port_to_flow') {
        return true;
      }
      if (keepFlowIds.has(e.target)) {
        return true;
      }
      if (hiddenFlowIds.has(e.target)) {
        return false;
      }
      return true;
    }),
    ...syntheticEdges,
  ];

  // Deduplicate edges after merge
  const edgeMap = new Map<string, NetworkMapEdge>();
  for (const edge of outEdges) {
    const key = edgeKey(edge);
    const existing = edgeMap.get(key);
    if (!existing) {
      edgeMap.set(key, edge);
      continue;
    }
    edgeMap.set(key, {
      ...existing,
      query_count: existing.query_count + edge.query_count,
      blocked_count: existing.blocked_count + edge.blocked_count,
    });
  }

  return {
    nodes: outNodes,
    edges: [...edgeMap.values()],
    meta: { flowsByPort, expansionByPort: effectiveExpansion },
  };
}

export function parseAggregatePortFromNode(node: NetworkMapNode): number | null {
  if (node.type !== 'flow_summary' && node.type !== 'flow_more') {
    return null;
  }
  return portFromNodeId(node.id);
}

export function nextPortDestExpansion(current: PortDestExpansion): PortDestExpansion {
  if (current === 'summary') {
    return 'partial';
  }
  return 'full';
}

export function portNodeIdForNumber(port: number, nodes: NetworkMapNode[]): string | null {
  const direct = globalPortNodeId('tcp', port);
  if (nodes.some((n) => n.id === direct)) {
    return direct;
  }
  const match = nodes.find((n) => n.type === 'port' && Number(n.label) === port);
  return match?.id ?? null;
}
