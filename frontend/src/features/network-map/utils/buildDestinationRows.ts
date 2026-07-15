import { NetworkMapEdge, NetworkMapNode, NetworkMapResponse } from '../types/networkMap';
import { parsePortLabel } from './flowLabels';

const PUBLIC_NETWORK_ID = 'infra:public_network';
const WIREGUARD_ID = 'infra:wireguard';
const DNS_RESOLVER_ID = 'infra:dns_resolver';

export type DestinationAction = 'allow' | 'block';
export type DestinationKind = 'domain' | 'port' | 'session';
export type DestinationSource = 'vpn' | 'trusttwin';

export interface DestinationRow {
  id: string;
  clientId: string;
  clientLabel: string;
  clientIp: string | null;
  appId: string | null;
  appLabel: string | null;
  destination: string;
  destinationId: string;
  destinationKind: DestinationKind;
  port: string | null;
  action: DestinationAction;
  queryCount: number;
  source: DestinationSource;
}

function clientSource(deviceId: string): DestinationSource {
  return deviceId.startsWith('device:twin:') ? 'trusttwin' : 'vpn';
}

function resolveDeviceForNode(
  nodeId: string,
  nodes: Map<string, NetworkMapNode>,
  appToDevice: Map<string, string>,
  edges: NetworkMapEdge[],
): NetworkMapNode | null {
  const direct = nodes.get(nodeId);
  if (direct?.type === 'device') {
    return direct;
  }
  if (direct?.type === 'app') {
    const deviceId = appToDevice.get(nodeId);
    return deviceId ? nodes.get(deviceId) ?? null : null;
  }
  // Walk inbound to_port / path_egress / flow_via_gateway toward a device.
  const inbound = edges.filter((e) => e.target === nodeId);
  for (const edge of inbound) {
    const found = resolveDeviceForNode(edge.source, nodes, appToDevice, edges);
    if (found) {
      return found;
    }
  }
  return null;
}

function resolveAppForNode(
  nodeId: string,
  nodes: Map<string, NetworkMapNode>,
  edges: NetworkMapEdge[],
): NetworkMapNode | null {
  const direct = nodes.get(nodeId);
  if (direct?.type === 'app') {
    return direct;
  }
  const inbound = edges.filter((e) => e.target === nodeId);
  for (const edge of inbound) {
    const src = nodes.get(edge.source);
    if (src?.type === 'app') {
      return src;
    }
    if (src?.type === 'device') {
      continue;
    }
    const found = resolveAppForNode(edge.source, nodes, edges);
    if (found) {
      return found;
    }
  }
  return null;
}

/** Build a flat who-talked-to-what table from the unified network graph. */
export function buildDestinationRows(graph: NetworkMapResponse | null): DestinationRow[] {
  if (!graph) {
    return [];
  }
  const nodes = new Map(graph.nodes.map((n) => [n.id, n]));
  const appToDevice = new Map<string, string>();
  for (const edge of graph.edges) {
    if (edge.kind === 'foreground') {
      appToDevice.set(edge.target, edge.source);
    }
  }

  const rows: DestinationRow[] = [];
  const seen = new Set<string>();

  const push = (row: DestinationRow) => {
    if (seen.has(row.id)) {
      return;
    }
    seen.add(row.id);
    rows.push(row);
  };

  for (const edge of graph.edges) {
    if (edge.kind !== 'dns' && edge.kind !== 'dns_direct') {
      continue;
    }
    const domain = nodes.get(edge.target);
    if (!domain || domain.type !== 'domain') {
      continue;
    }
    const app = nodes.get(edge.source)?.type === 'app' ? nodes.get(edge.source)! : null;
    const device =
      app != null
        ? nodes.get(appToDevice.get(app.id) ?? '') ?? null
        : nodes.get(edge.source)?.type === 'device'
          ? nodes.get(edge.source)!
          : null;
    if (!device || device.type !== 'device') {
      continue;
    }
    const blocked = Boolean(domain.blocked) || edge.blocked_count > 0;
    push({
      id: `${device.id}|${app?.id ?? '-'}|${domain.id}`,
      clientId: device.id,
      clientLabel: device.label,
      clientIp: device.client_ip ?? null,
      appId: app?.id ?? null,
      appLabel: app?.label ?? null,
      destination: domain.label,
      destinationId: domain.id,
      destinationKind: 'domain',
      port: null,
      action: blocked ? 'block' : 'allow',
      queryCount: edge.query_count,
      source: clientSource(device.id),
    });
  }

  for (const edge of graph.edges) {
    if (edge.kind !== 'port_to_flow') {
      continue;
    }
    const port = nodes.get(edge.source);
    const flow = nodes.get(edge.target);
    if (!port || port.type !== 'port' || !flow) {
      continue;
    }
    const toPort = graph.edges.find((e) => e.kind === 'to_port' && e.target === port.id);
    const anchorId = toPort?.source ?? edge.source;
    const device = resolveDeviceForNode(anchorId, nodes, appToDevice, graph.edges);
    if (!device) {
      continue;
    }
    const app = resolveAppForNode(anchorId, nodes, graph.edges);
    const processName = flow.process_name?.trim() || null;
    const processSlug = flow.app_slug?.trim() || null;
    const appLabel = app?.label ?? processName;
    const appId =
      app?.id ?? (processSlug ? `app:${processSlug}` : processName ? `app:${processName}` : null);
    // Prefer service-only destination label when process is shown in its own column.
    let destination = flow.label;
    if (processName && destination.startsWith(`${processName} · `)) {
      destination = destination.slice(processName.length + 3);
    }
    push({
      id: `${device.id}|${appId ?? '-'}|${flow.id}`,
      clientId: device.id,
      clientLabel: device.label,
      clientIp: device.client_ip ?? null,
      appId,
      appLabel,
      destination,
      destinationId: flow.id,
      destinationKind: flow.type === 'flow' || flow.type === 'flow_summary' ? 'session' : 'port',
      port: parsePortLabel(port.label) != null ? String(parsePortLabel(port.label)) : port.label,
      action: 'allow',
      queryCount: edge.query_count,
      source: clientSource(device.id),
    });
  }

  // Group by client, then blocked first within client, then process, then destination.
  rows.sort((a, b) => {
    const clientCmp = a.clientLabel.localeCompare(b.clientLabel);
    if (clientCmp !== 0) {
      return clientCmp;
    }
    if (a.action !== b.action) {
      return a.action === 'block' ? -1 : 1;
    }
    const appCmp = (a.appLabel ?? '\uffff').localeCompare(b.appLabel ?? '\uffff');
    if (appCmp !== 0) {
      return appCmp;
    }
    return a.destination.localeCompare(b.destination);
  });

  return rows;
}

export function listClientsFromRows(
  rows: DestinationRow[],
): { id: string; label: string; source: DestinationSource }[] {
  const map = new Map<string, { id: string; label: string; source: DestinationSource }>();
  for (const row of rows) {
    if (!map.has(row.clientId)) {
      map.set(row.clientId, {
        id: row.clientId,
        label: row.clientLabel,
        source: row.source,
      });
    }
  }
  return [...map.values()].sort((a, b) => a.label.localeCompare(b.label));
}

/** Keep only nodes/edges reachable forward from the selected client device. */
export function filterGraphByClient(
  graph: NetworkMapResponse,
  clientId: string | 'all',
): NetworkMapResponse {
  if (clientId === 'all') {
    return graph;
  }
  const nodes = new Map(graph.nodes.map((n) => [n.id, n]));
  if (!nodes.has(clientId)) {
    return { ...graph, nodes: [], edges: [] };
  }

  const forward = new Set<string>([clientId]);
  const queue = [clientId];
  while (queue.length > 0) {
    const cur = queue.shift()!;
    for (const edge of graph.edges) {
      if (edge.source !== cur || forward.has(edge.target)) {
        continue;
      }
      const tgt = nodes.get(edge.target);
      if (!tgt) {
        continue;
      }
      if (tgt.type === 'device' && tgt.id !== clientId) {
        continue;
      }
      forward.add(edge.target);
      queue.push(edge.target);
    }
  }

  const filteredNodes = graph.nodes.filter((n) => forward.has(n.id));
  const filteredIds = new Set(filteredNodes.map((n) => n.id));
  const filteredEdges = graph.edges.filter(
    (e) => filteredIds.has(e.source) && filteredIds.has(e.target),
  );

  return {
    ...graph,
    nodes: filteredNodes,
    edges: filteredEdges,
  };
}

function subgraphFromIds(
  graph: NetworkMapResponse,
  keep: Set<string>,
): NetworkMapResponse {
  const nodes = graph.nodes.filter((n) => keep.has(n.id));
  const ids = new Set(nodes.map((n) => n.id));
  const edges = graph.edges.filter((e) => ids.has(e.source) && ids.has(e.target));
  return { ...graph, nodes, edges };
}

/**
 * Minimal path for the inspector:
 * - TrustTwin default: Client → LAN → Internet (no port fan-out)
 * - TrustTwin + selected port/session row: spine + that port + session only
 * - VPN default: Client → apps → domains + WireGuard/EC2 (no session pins)
 * - VPN + selected row: path for that destination only
 */
export function focusPathGraph(
  graph: NetworkMapResponse,
  clientId: string | 'all',
  selectedRow: DestinationRow | null,
): NetworkMapResponse {
  const scoped = filterGraphByClient(graph, clientId);
  if (clientId === 'all' || scoped.nodes.length === 0) {
    return scoped;
  }

  const isTwin = clientId.startsWith('device:twin:');
  const keep = new Set<string>([clientId]);

  // Egress / VPN spine.
  for (const node of scoped.nodes) {
    if (node.type === 'tunnel' || node.type === 'gateway') {
      keep.add(node.id);
    }
  }
  // Shared infra ids may use fixed names.
  for (const id of [PUBLIC_NETWORK_ID, WIREGUARD_ID, DNS_RESOLVER_ID]) {
    if (scoped.nodes.some((n) => n.id === id)) {
      keep.add(id);
    }
  }

  const row =
    selectedRow && selectedRow.clientId === clientId ? selectedRow : null;

  if (isTwin) {
    if (row && (row.destinationKind === 'session' || row.destinationKind === 'port')) {
      if (row.appId) {
        keep.add(row.appId);
      }
      keep.add(row.destinationId);
      if (row.port) {
        const portNum = Number(row.port);
        const portNode = scoped.nodes.find(
          (n) => n.type === 'port' && parsePortLabel(n.label) === portNum,
        );
        if (portNode) {
          keep.add(portNode.id);
        }
      }
      // Session row destination is the flow node; ensure linked port.
      for (const edge of scoped.edges) {
        if (edge.kind === 'port_to_flow' && edge.target === row.destinationId) {
          keep.add(edge.source);
        }
        if (edge.kind === 'to_port' && keep.has(edge.target)) {
          keep.add(edge.source);
        }
      }
    }
    return subgraphFromIds(scoped, keep);
  }

  // VPN clients.
  if (row) {
    if (row.appId) {
      keep.add(row.appId);
    }
    keep.add(row.destinationId);
    if (row.port) {
      const portNum = Number(row.port);
      const portNode = scoped.nodes.find(
        (n) => n.type === 'port' && parsePortLabel(n.label) === portNum,
      );
      if (portNode) {
        keep.add(portNode.id);
      }
    }
    for (const edge of scoped.edges) {
      if (edge.kind === 'port_to_flow' && edge.target === row.destinationId) {
        keep.add(edge.source);
      }
    }
    return subgraphFromIds(scoped, keep);
  }

  // VPN default: destinations as domains/apps, not every L4 session pin.
  for (const node of scoped.nodes) {
    if (node.type === 'app' || node.type === 'domain') {
      keep.add(node.id);
    }
  }
  return subgraphFromIds(scoped, keep);
}
