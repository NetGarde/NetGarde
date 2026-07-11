import { NetworkMapEdge, NetworkMapNode } from '../types/networkMap';
import { globalPortNodeId, parsePortLabel } from './flowLabels';
import { edgeKey } from './whatIfSimulation';

export type PortDestExpansion = 'summary' | 'partial' | 'full';

export const FLOW_DEST_TOP_N = 5;

export interface FlowDestinationAggregateMeta {
  flowsByHub: Map<string, string[]>;
  expansionByHub: Record<string, PortDestExpansion>;
}

export interface AggregatedFlowGraph {
  nodes: NetworkMapNode[];
  edges: NetworkMapEdge[];
  meta: FlowDestinationAggregateMeta;
}

function summaryNodeId(hubKey: string): string {
  return `flow_summary:${hubKey}`;
}

function moreNodeId(hubKey: string): string {
  return `flow_more:${hubKey}`;
}

function hubKeyFromNodeId(nodeId: string): string | null {
  const match = nodeId.match(/^flow_(?:summary|more):(.+)$/);
  return match?.[1] ?? null;
}

function defaultExpansion(flowCount: number): PortDestExpansion {
  if (flowCount <= FLOW_DEST_TOP_N) {
    return 'full';
  }
  return 'summary';
}

function resolveExpansion(
  hubKey: string,
  flowCount: number,
  overrides: Record<string, PortDestExpansion>,
): PortDestExpansion {
  const chosen = overrides[hubKey] ?? defaultExpansion(flowCount);
  if (flowCount <= FLOW_DEST_TOP_N) {
    return 'full';
  }
  return chosen;
}

function flowsFromHub(
  edges: NetworkMapEdge[],
  hubId: string,
  flowKind: 'port_to_flow' | 'gateway_to_flow',
  flowNodes: Map<string, NetworkMapNode>,
): NetworkMapNode[] {
  const ids = edges.filter((e) => e.kind === flowKind && e.source === hubId).map((e) => e.target);
  return ids
    .map((id) => flowNodes.get(id))
    .filter((node): node is NetworkMapNode => node != null)
    .sort((a, b) => a.label.localeCompare(b.label));
}

function aggregateHubFlows(
  hubId: string,
  hubKey: string,
  flowKind: 'port_to_flow' | 'gateway_to_flow',
  flows: NetworkMapNode[],
  expansion: PortDestExpansion,
  hiddenFlowIds: Set<string>,
  keepFlowIds: Set<string>,
  syntheticNodes: NetworkMapNode[],
  syntheticEdges: NetworkMapEdge[],
  summaryLabel: string,
): void {
  const count = flows.length;
  if (count === 0) {
    return;
  }

  if (expansion === 'summary') {
    for (const flow of flows) {
      hiddenFlowIds.add(flow.id);
    }
    syntheticNodes.push({
      id: summaryNodeId(hubKey),
      type: 'flow_summary',
      label: summaryLabel,
    });
    syntheticEdges.push({
      source: hubId,
      target: summaryNodeId(hubKey),
      kind: flowKind,
      query_count: count,
      blocked_count: 0,
    });
    return;
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
        id: moreNodeId(hubKey),
        type: 'flow_more',
        label: `+${rest.length} more`,
      });
      syntheticEdges.push({
        source: hubId,
        target: moreNodeId(hubKey),
        kind: flowKind,
        query_count: rest.length,
        blocked_count: 0,
      });
    }
    return;
  }

  for (const flow of flows) {
    keepFlowIds.add(flow.id);
  }
}

/** Collapse destination flows into summary / top-N / full views (by port hub or EC2 gateway). */
export function aggregateFlowDestinations(
  nodes: NetworkMapNode[],
  edges: NetworkMapEdge[],
  expansionByHub: Record<string, PortDestExpansion> = {},
): AggregatedFlowGraph {
  const flowNodes = new Map(nodes.filter((n) => n.type === 'flow').map((n) => [n.id, n]));
  const portNodes = nodes.filter((n) => n.type === 'port');
  const gatewayNodes = nodes.filter((n) => n.type === 'gateway');
  const hiddenFlowIds = new Set<string>();

  if (flowNodes.size === 0) {
    return {
      nodes,
      edges,
      meta: { flowsByHub: new Map(), expansionByHub: {} },
    };
  }

  const flowsByHub = new Map<string, string[]>();
  const effectiveExpansion: Record<string, PortDestExpansion> = {};
  const keepFlowIds = new Set<string>();
  const syntheticNodes: NetworkMapNode[] = [];
  const syntheticEdges: NetworkMapEdge[] = [];

  if (portNodes.length > 0) {
    for (const portNode of portNodes) {
      const portNum = parsePortLabel(portNode.label);
      if (portNum == null) {
        continue;
      }
      const hubKey = String(portNum);
      const flows = flowsFromHub(edges, portNode.id, 'port_to_flow', flowNodes);
      flowsByHub.set(
        hubKey,
        flows.map((f) => f.id),
      );
      effectiveExpansion[hubKey] = resolveExpansion(hubKey, flows.length, expansionByHub);
    }

    for (const portNode of portNodes) {
      const portNum = parsePortLabel(portNode.label);
      if (portNum == null) {
        continue;
      }
      const hubKey = String(portNum);
      const flows = flowsFromHub(edges, portNode.id, 'port_to_flow', flowNodes);
      aggregateHubFlows(
        portNode.id,
        hubKey,
        'port_to_flow',
        flows,
        effectiveExpansion[hubKey],
        hiddenFlowIds,
        keepFlowIds,
        syntheticNodes,
        syntheticEdges,
        `${flows.length} connection${flows.length === 1 ? '' : 's'} on ${portNum}`,
      );
    }
  } else {
    for (const gateway of gatewayNodes) {
      const hubKey = `gateway:${gateway.id}`;
      const flows = flowsFromHub(edges, gateway.id, 'gateway_to_flow', flowNodes);
      if (flows.length === 0) {
        continue;
      }
      flowsByHub.set(
        hubKey,
        flows.map((f) => f.id),
      );
      effectiveExpansion[hubKey] = resolveExpansion(hubKey, flows.length, expansionByHub);
      aggregateHubFlows(
        gateway.id,
        hubKey,
        'gateway_to_flow',
        flows,
        effectiveExpansion[hubKey],
        hiddenFlowIds,
        keepFlowIds,
        syntheticNodes,
        syntheticEdges,
        `${flows.length} live session${flows.length === 1 ? '' : 's'}`,
      );
    }
  }

  const flowEdgeKinds = new Set(['port_to_flow', 'gateway_to_flow']);
  const outNodes = [
    ...nodes.filter((n) => n.type !== 'flow' || keepFlowIds.has(n.id)),
    ...syntheticNodes,
  ];

  const outEdges = [
    ...edges.filter((e) => {
      if (!flowEdgeKinds.has(e.kind)) {
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
    meta: { flowsByHub, expansionByHub: effectiveExpansion },
  };
}

export function parseAggregateHubFromNode(node: NetworkMapNode): string | null {
  if (node.type !== 'flow_summary' && node.type !== 'flow_more') {
    return null;
  }
  return hubKeyFromNodeId(node.id);
}

/** @deprecated use parseAggregateHubFromNode */
export function parseAggregatePortFromNode(node: NetworkMapNode): number | null {
  const hub = parseAggregateHubFromNode(node);
  if (hub == null || hub.startsWith('gateway:')) {
    return null;
  }
  const port = Number(hub);
  return Number.isFinite(port) ? port : null;
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
  const match = nodes.find((n) => n.type === 'port' && parsePortLabel(n.label) === port);
  return match?.id ?? null;
}
