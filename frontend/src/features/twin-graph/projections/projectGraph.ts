import { NetworkMapEdge, NetworkMapNode, NetworkMapResponse } from '../../network-map/types/networkMap';
import { globalPortNodeId } from '../../network-map/utils/flowLabels';
import { edgeKey } from '../../network-map/utils/whatIfSimulation';
import { TwinGraphIndex } from '../graph/TwinGraphIndex';
import { TwinEdge, TwinGraphSnapshot, TwinNode } from '../types/twinGraph';

export type TwinProjectionMode = 'attribution' | 'path' | 'flow' | 'unified';

const EC2_GATEWAY_ID = 'infra:ec2_gateway';
const DNS_RESOLVER_ID = 'infra:dns_resolver';
const PUBLIC_NETWORK_ID = 'infra:public_network';

function isTrustTwinDeviceId(nodeId: string): boolean {
  return nodeId.startsWith('device:twin:');
}

function isTrustTwinNode(node: TwinNode | undefined): boolean {
  return node?.properties?.source === 'trusttwin';
}

const OBSERVED_RELATION_TO_KIND: Partial<Record<TwinEdge['relation'], NetworkMapEdge['kind']>> = {
  runs: 'foreground',
  queries: 'dns',
  queries_direct: 'dns_direct',
  correlates: 'dns_to_flow',
  opens: 'flow_session',
  opens_direct: 'flow_session',
};

function edgeCounts(edge: TwinEdge): Pick<NetworkMapEdge, 'query_count' | 'blocked_count'> {
  const blocked = Number(edge.properties.blocked_count ?? 0);
  return {
    query_count: Math.max(1, Math.round(edge.weight)),
    blocked_count: Number.isFinite(blocked) ? blocked : 0,
  };
}

function twinDeviceToMap(node: TwinNode): NetworkMapNode {
  const clientIp =
    (node.properties.client_ip as string | undefined) ||
    (node.properties.public_ip as string | undefined) ||
    null;
  const deviceId = node.properties.device_id;
  return {
    id: node.id,
    type: 'device',
    label: node.label,
    client_ip: clientIp,
    // Non-twin devices use numeric PKs; TrustTwin agents use string ids in properties.
    device_id: typeof deviceId === 'number' ? deviceId : null,
    fresh: node.properties.fresh as boolean | undefined,
    blocked: node.properties.blocked as boolean | undefined,
  };
}

function twinAppToMap(node: TwinNode): NetworkMapNode {
  return {
    id: node.id,
    type: 'app',
    label: node.label,
    app_slug: (node.properties.slug as string) ?? (node.properties.app_slug as string) ?? null,
  };
}

function twinDomainToMap(node: TwinNode): NetworkMapNode {
  return {
    id: node.id,
    type: 'domain',
    label: node.label,
    blocked: node.properties.blocked as boolean | undefined,
  };
}

function twinInfraToMap(node: TwinNode): NetworkMapNode | null {
  const kind = String(node.properties.kind ?? '');
  if (kind === 'ec2_gateway') {
    return { id: node.id, type: 'tunnel', label: node.label || 'EC2 Gateway' };
  }
  if (kind === 'dns_resolver') {
    return { id: node.id, type: 'gateway', label: 'EC2 DNS' };
  }
  if (kind === 'public_network') {
    return { id: node.id, type: 'gateway', label: node.label || 'Internet' };
  }
  // TrustTwin egress link only (security path, not host posture).
  if (kind === 'tt_lan') {
    return { id: node.id, type: 'tunnel', label: node.label };
  }
  // Ignore legacy WireGuard / host-posture kinds if present in older snapshots.
  if (kind === 'wireguard' || kind.startsWith('tt_')) {
    return null;
  }
  return { id: node.id, type: 'gateway', label: node.label };
}

/** Apps that participate in DNS or L4 destinations (who talked to what). */
function networkActiveAppIds(snapshot: TwinGraphSnapshot): Set<string> {
  const ids = new Set<string>();
  for (const edge of snapshot.edges) {
    if (
      edge.relation !== 'queries' &&
      edge.relation !== 'queries_direct' &&
      edge.relation !== 'opens' &&
      edge.relation !== 'opens_direct' &&
      edge.relation !== 'correlates'
    ) {
      continue;
    }
    if (edge.source_id.startsWith('app:')) {
      ids.add(edge.source_id);
    }
    if (edge.target_id.startsWith('app:')) {
      ids.add(edge.target_id);
    }
  }
  return ids;
}

function portLabelFromL4(l4Node: TwinNode, port: number): string {
  const service = String(l4Node.properties.service ?? '').trim();
  if (service) {
    return `${service} :${port}`;
  }
  return String(port);
}

function mapTrustTwinNode(node: TwinNode): NetworkMapNode | null {
  if (node.entity_type === 'device') {
    return twinDeviceToMap(node);
  }
  if (node.entity_type === 'app') {
    return twinAppToMap(node);
  }
  if (node.entity_type === 'domain') {
    return twinDomainToMap(node);
  }
  if (node.entity_type === 'infra_component') {
    return twinInfraToMap(node);
  }
  if (node.entity_type === 'ip_address' && isTrustTwinNode(node)) {
    return { id: node.id, type: 'flow', label: node.label };
  }
  return null;
}

function twinFlowSessionToMap(node: TwinNode, destinationLabel: string): NetworkMapNode {
  const processName = String(node.properties.app_name ?? '').trim() || null;
  const appSlug = String(node.properties.app_slug ?? '').trim() || null;
  // TrustTwin port aggregates have no remote IP — keep the prebuilt label.
  if (node.properties.aggregate || node.properties.source === 'trusttwin') {
    return {
      id: node.id,
      type: 'flow',
      label: node.label,
      process_name: processName,
      app_slug: appSlug,
    };
  }
  const protocol = String(node.properties.protocol ?? 'tcp');
  const port = Number(node.properties.dest_port ?? 0);
  return {
    id: node.id,
    type: 'flow',
    label: destinationLabel || `${protocol.toUpperCase()}/${port} → ${node.properties.dest_ip ?? ''}`,
    process_name: processName,
    app_slug: appSlug,
  };
}

function upsertMapEdge(map: Map<string, NetworkMapEdge>, edge: NetworkMapEdge): void {
  const key = edgeKey(edge);
  const existing = map.get(key);
  if (!existing) {
    map.set(key, edge);
    return;
  }
  map.set(key, {
    ...existing,
    query_count: existing.query_count + edge.query_count,
    blocked_count: existing.blocked_count + edge.blocked_count,
  });
}

/** Project canonical twin graph to attribution view (device → app → domain). */
export function projectAttributionGraph(
  snapshot: TwinGraphSnapshot,
  override?: NetworkMapResponse | null,
): NetworkMapResponse {
  if (override) {
    return override;
  }

  const nodeMap = new Map<string, NetworkMapNode>();
  const edgeMap = new Map<string, NetworkMapEdge>();

  for (const node of snapshot.nodes) {
    if (node.layer !== 'observed') {
      continue;
    }
    if (node.entity_type === 'device') {
      nodeMap.set(node.id, twinDeviceToMap(node));
    } else if (node.entity_type === 'app') {
      nodeMap.set(node.id, twinAppToMap(node));
    } else if (node.entity_type === 'domain') {
      nodeMap.set(node.id, twinDomainToMap(node));
    }
  }

  for (const edge of snapshot.edges) {
    if (edge.layer !== 'observed') {
      continue;
    }
    const kind = OBSERVED_RELATION_TO_KIND[edge.relation];
    if (!kind || !nodeMap.has(edge.source_id) || !nodeMap.has(edge.target_id)) {
      continue;
    }
    upsertMapEdge(edgeMap, {
      source: edge.source_id,
      target: edge.target_id,
      kind,
      ...edgeCounts(edge),
    });
  }

  return {
    generated_at: snapshot.generated_at,
    minutes: snapshot.window_minutes,
    nodes: [...nodeMap.values()],
    edges: [...edgeMap.values()],
  };
}

/** Project twin graph to path view using infra nodes from the canonical graph. */
export function projectPathGraph(
  snapshot: TwinGraphSnapshot,
  attribution: NetworkMapResponse,
): NetworkMapResponse {
  const nodeMap = new Map<string, NetworkMapNode>();
  const edgeMap = new Map<string, NetworkMapEdge>();

  for (const node of attribution.nodes) {
    nodeMap.set(node.id, node);
  }

  for (const node of snapshot.nodes) {
    if (node.entity_type === 'infra_component') {
      const mapped = twinInfraToMap(node);
      if (mapped) {
        nodeMap.set(mapped.id, mapped);
      }
    }
  }

  for (const edge of attribution.edges) {
    if (edge.kind === 'foreground') {
      upsertMapEdge(edgeMap, edge);
    }
  }

  let hasDnsFlow = false;
  for (const edge of attribution.edges) {
    if (edge.kind !== 'dns' && edge.kind !== 'dns_direct') {
      continue;
    }
    hasDnsFlow = true;
    upsertMapEdge(edgeMap, {
      source: edge.source,
      target: EC2_GATEWAY_ID,
      kind: 'path_egress',
      query_count: edge.query_count,
      blocked_count: 0,
    });
  }

  if (hasDnsFlow && nodeMap.has(EC2_GATEWAY_ID) && nodeMap.has(DNS_RESOLVER_ID)) {
    upsertMapEdge(edgeMap, {
      source: EC2_GATEWAY_ID,
      target: DNS_RESOLVER_ID,
      kind: 'path_tunnel',
      query_count: 0,
      blocked_count: 0,
    });
  }

  return {
    generated_at: snapshot.generated_at,
    minutes: snapshot.window_minutes,
    nodes: [...nodeMap.values()],
    edges: [...edgeMap.values()],
  };
}

/** Project twin graph to flow view (device → app → EC2 DNS → port → destination). */
export function projectFlowGraph(snapshot: TwinGraphSnapshot): NetworkMapResponse {
  const index = new TwinGraphIndex(snapshot);
  const nodeMap = new Map<string, NetworkMapNode>();
  const edgeMap = new Map<string, NetworkMapEdge>();
  const flowParticipantIds = new Set<string>();

  const ensureGateway = () => {
    const gateway = snapshot.nodes.find(
      (node) => node.entity_type === 'infra_component' && node.properties.kind === 'dns_resolver',
    );
    if (!gateway) {
      return;
    }
    nodeMap.set(gateway.id, { id: gateway.id, type: 'gateway', label: 'EC2 DNS' });
  };

  const ensureTwinNode = (nodeId: string) => {
    if (nodeMap.has(nodeId)) {
      return;
    }
    const twin = index.nodes.get(nodeId);
    if (!twin) {
      return;
    }
    if (twin.entity_type === 'device') {
      nodeMap.set(nodeId, twinDeviceToMap(twin));
    } else if (twin.entity_type === 'app') {
      nodeMap.set(nodeId, twinAppToMap(twin));
    }
  };

  const linkViaGateway = (
    sourceId: string,
    portId: string,
    counts: Pick<NetworkMapEdge, 'query_count' | 'blocked_count'>,
  ) => {
    ensureTwinNode(sourceId);
    flowParticipantIds.add(sourceId);
    upsertMapEdge(edgeMap, {
      source: sourceId,
      target: DNS_RESOLVER_ID,
      kind: 'flow_via_gateway',
      ...counts,
    });
    upsertMapEdge(edgeMap, {
      source: DNS_RESOLVER_ID,
      target: portId,
      kind: 'to_port',
      ...counts,
    });
  };

  const destLabelByFlow = new Map<string, string>();
  for (const edge of snapshot.edges) {
    if (edge.relation !== 'destinates') {
      continue;
    }
    const ipNode = index.nodes.get(edge.target_id);
    if (ipNode) {
      destLabelByFlow.set(edge.source_id, ipNode.label);
    }
  }

  const flowSessions = snapshot.nodes.filter((node) => node.entity_type === 'flow_session');
  if (flowSessions.length > 0) {
    ensureGateway();
  }

  for (const node of flowSessions) {
    const destination = destLabelByFlow.get(node.id) ?? String(node.properties.dest_ip ?? node.label);
    nodeMap.set(node.id, twinFlowSessionToMap(node, destination));

    const serviceEdge = snapshot.edges.find(
      (edge) => edge.relation === 'uses_service' && edge.source_id === node.id,
    );
    if (!serviceEdge) {
      continue;
    }
    const l4Node = index.nodes.get(serviceEdge.target_id);
    if (!l4Node) {
      continue;
    }
    const protocol = String(l4Node.properties.protocol ?? 'tcp');
    const port = Number(l4Node.properties.port ?? 0);
    const portId = globalPortNodeId(protocol, port);
    nodeMap.set(portId, { id: portId, type: 'port', label: String(port) });
  }

  for (const edge of snapshot.edges) {
    if (edge.relation !== 'opens' && edge.relation !== 'opens_direct' && edge.relation !== 'correlates') {
      continue;
    }
    const flowId = edge.target_id;
    const flowNode = index.nodes.get(flowId);
    if (!flowNode || flowNode.entity_type !== 'flow_session') {
      continue;
    }
    const serviceEdge = snapshot.edges.find(
      (item) => item.relation === 'uses_service' && item.source_id === flowId,
    );
    const l4Node = serviceEdge ? index.nodes.get(serviceEdge.target_id) : null;
    if (!l4Node) {
      continue;
    }
    const protocol = String(l4Node.properties.protocol ?? 'tcp');
    const port = Number(l4Node.properties.port ?? 0);
    const portId = globalPortNodeId(protocol, port);
    const counts = edgeCounts(edge);

    if (edge.relation === 'correlates') {
      const upstream = snapshot.edges.filter(
        (item) =>
          (item.relation === 'queries' || item.relation === 'queries_direct') &&
          item.target_id === edge.source_id,
      );
      if (upstream.length > 0) {
        for (const dnsEdge of upstream) {
          linkViaGateway(dnsEdge.source_id, portId, edgeCounts(dnsEdge));
        }
      } else {
        const opener = snapshot.edges.find(
          (item) =>
            (item.relation === 'opens' || item.relation === 'opens_direct') &&
            item.target_id === flowId,
        );
        if (opener) {
          linkViaGateway(opener.source_id, portId, counts);
        }
      }
    } else {
      linkViaGateway(edge.source_id, portId, counts);
    }

    upsertMapEdge(edgeMap, {
      source: portId,
      target: flowId,
      kind: 'port_to_flow',
      ...counts,
    });
  }

  for (const edge of snapshot.edges) {
    if (edge.relation !== 'runs') {
      continue;
    }
    if (!flowParticipantIds.has(edge.target_id)) {
      continue;
    }
    ensureTwinNode(edge.source_id);
    ensureTwinNode(edge.target_id);
    flowParticipantIds.add(edge.source_id);
    upsertMapEdge(edgeMap, {
      source: edge.source_id,
      target: edge.target_id,
      kind: 'foreground',
      ...edgeCounts(edge),
    });
  }

  const connectedIds = new Set<string>();
  for (const edge of edgeMap.values()) {
    connectedIds.add(edge.source);
    connectedIds.add(edge.target);
  }
  for (const nodeId of [...nodeMap.keys()]) {
    if (!connectedIds.has(nodeId)) {
      nodeMap.delete(nodeId);
    }
  }

  return {
    generated_at: snapshot.generated_at,
    minutes: snapshot.window_minutes,
    nodes: [...nodeMap.values()],
    edges: [...edgeMap.values()],
  };
}

/** Security map: who talked to what (DNS, ports, sessions, path) — not host posture. */
export function projectUnifiedGraph(
  snapshot: TwinGraphSnapshot,
  attributionOverride?: NetworkMapResponse | null,
): NetworkMapResponse {
  const attribution = projectAttributionGraph(snapshot, attributionOverride);
  const index = new TwinGraphIndex(snapshot);
  const nodeMap = new Map<string, NetworkMapNode>();
  const edgeMap = new Map<string, NetworkMapEdge>();
  const flowParticipantIds = new Set<string>();
  const activeApps = networkActiveAppIds(snapshot);

  for (const node of attribution.nodes) {
    // Only apps that have destinations (DNS/flows). Skip TrustTwin focus-only apps.
    if (node.type === 'app' && !activeApps.has(node.id)) {
      continue;
    }
    // Policy chips are not part of the security destination graph.
    if (node.type === 'policy') {
      continue;
    }
    nodeMap.set(node.id, node);
  }

  for (const node of snapshot.nodes) {
    if (node.entity_type === 'infra_component') {
      const mapped = twinInfraToMap(node);
      if (mapped) {
        nodeMap.set(mapped.id, mapped);
      }
    }
  }

  for (const edge of attribution.edges) {
    if (!nodeMap.has(edge.source) || !nodeMap.has(edge.target)) {
      continue;
    }
    upsertMapEdge(edgeMap, edge);
  }

  let hasDnsPath = false;
  for (const edge of attribution.edges) {
    if (edge.kind !== 'dns' && edge.kind !== 'dns_direct') {
      continue;
    }
    hasDnsPath = true;
    if (nodeMap.has(EC2_GATEWAY_ID)) {
      upsertMapEdge(edgeMap, {
        source: edge.source,
        target: EC2_GATEWAY_ID,
        kind: 'path_egress',
        query_count: edge.query_count,
        blocked_count: 0,
      });
    }
  }
  if (hasDnsPath && nodeMap.has(EC2_GATEWAY_ID) && nodeMap.has(DNS_RESOLVER_ID)) {
    upsertMapEdge(edgeMap, {
      source: EC2_GATEWAY_ID,
      target: DNS_RESOLVER_ID,
      kind: 'path_tunnel',
      query_count: 0,
      blocked_count: 0,
    });
    for (const edge of attribution.edges) {
      if (edge.kind !== 'dns' && edge.kind !== 'dns_direct') {
        continue;
      }
      upsertMapEdge(edgeMap, {
        source: DNS_RESOLVER_ID,
        target: edge.target,
        kind: 'path_forward',
        query_count: edge.query_count,
        blocked_count: edge.blocked_count,
      });
    }
  }

  const ensureGateway = () => {
    const gateway = snapshot.nodes.find(
      (node) => node.entity_type === 'infra_component' && node.properties.kind === 'dns_resolver',
    );
    if (!gateway) {
      return;
    }
    nodeMap.set(gateway.id, { id: gateway.id, type: 'gateway', label: 'EC2 DNS' });
  };

  const ensureTwinNode = (nodeId: string) => {
    if (nodeMap.has(nodeId)) {
      return;
    }
    const twin = index.nodes.get(nodeId);
    if (!twin) {
      return;
    }
    const mapped = mapTrustTwinNode(twin);
    if (mapped) {
      nodeMap.set(nodeId, mapped);
    }
  };

  const linkViaGateway = (
    sourceId: string,
    portId: string,
    counts: Pick<NetworkMapEdge, 'query_count' | 'blocked_count'>,
  ) => {
    ensureGateway();
    ensureTwinNode(sourceId);
    flowParticipantIds.add(sourceId);
    upsertMapEdge(edgeMap, {
      source: sourceId,
      target: DNS_RESOLVER_ID,
      kind: 'flow_via_gateway',
      ...counts,
    });
    upsertMapEdge(edgeMap, {
      source: DNS_RESOLVER_ID,
      target: portId,
      kind: 'to_port',
      ...counts,
    });
  };

  /**
   * TrustTwin egress: Internet → remote port → session aggregate.
   * Ports must not hang off the client (that reads as a local peer).
   */
  const linkTrustTwinPort = (
    _sourceId: string,
    portId: string,
    flowId: string,
    counts: Pick<NetworkMapEdge, 'query_count' | 'blocked_count'>,
  ) => {
    const infra = index.nodes.get(PUBLIC_NETWORK_ID);
    if (infra) {
      const mapped = twinInfraToMap(infra);
      if (mapped) {
        nodeMap.set(mapped.id, mapped);
      }
    }
    flowParticipantIds.add(PUBLIC_NETWORK_ID);
    upsertMapEdge(edgeMap, {
      source: PUBLIC_NETWORK_ID,
      target: portId,
      kind: 'to_port',
      ...counts,
    });
    upsertMapEdge(edgeMap, {
      source: portId,
      target: flowId,
      kind: 'port_to_flow',
      ...counts,
    });
  };

  const destLabelByFlow = new Map<string, string>();
  for (const edge of snapshot.edges) {
    if (edge.relation !== 'destinates') {
      continue;
    }
    const ipNode = index.nodes.get(edge.target_id);
    if (ipNode) {
      destLabelByFlow.set(edge.source_id, ipNode.label);
    }
  }

  const flowSessions = snapshot.nodes.filter((node) => node.entity_type === 'flow_session');
  const hasEndpointFlows = flowSessions.some((node) => !isTrustTwinNode(node));
  if (hasEndpointFlows) {
    ensureGateway();
  }

  for (const node of flowSessions) {
    const destination = destLabelByFlow.get(node.id) ?? String(node.properties.dest_ip ?? node.label);
    nodeMap.set(node.id, twinFlowSessionToMap(node, destination));

    const serviceEdge = snapshot.edges.find(
      (edge) => edge.relation === 'uses_service' && edge.source_id === node.id,
    );
    if (!serviceEdge) {
      continue;
    }
    const l4Node = index.nodes.get(serviceEdge.target_id);
    if (!l4Node) {
      continue;
    }
    const protocol = String(l4Node.properties.protocol ?? 'tcp');
    const port = Number(l4Node.properties.port ?? 0);
    const portId = globalPortNodeId(protocol, port);
    nodeMap.set(portId, {
      id: portId,
      type: 'port',
      label: portLabelFromL4(l4Node, port),
    });
  }

  for (const edge of snapshot.edges) {
    if (edge.relation === 'correlates') {
      const flowId = edge.target_id;
      const domainId = edge.source_id;
      if (nodeMap.has(domainId) && nodeMap.has(flowId)) {
        upsertMapEdge(edgeMap, {
          source: domainId,
          target: flowId,
          kind: 'dns_to_flow',
          ...edgeCounts(edge),
        });
      }
    }
    if (edge.relation !== 'opens' && edge.relation !== 'opens_direct' && edge.relation !== 'correlates') {
      continue;
    }
    const flowId = edge.target_id;
    const flowNode = index.nodes.get(flowId);
    if (!flowNode || flowNode.entity_type !== 'flow_session') {
      continue;
    }
    const serviceEdge = snapshot.edges.find(
      (item) => item.relation === 'uses_service' && item.source_id === flowId,
    );
    const l4Node = serviceEdge ? index.nodes.get(serviceEdge.target_id) : null;
    if (!l4Node) {
      continue;
    }
    const protocol = String(l4Node.properties.protocol ?? 'tcp');
    const port = Number(l4Node.properties.port ?? 0);
    const portId = globalPortNodeId(protocol, port);
    nodeMap.set(portId, {
      id: portId,
      type: 'port',
      label: portLabelFromL4(l4Node, port),
    });
    const counts = edgeCounts(edge);
    const trustTwinFlow = isTrustTwinNode(flowNode);

    if (trustTwinFlow) {
      if (edge.relation === 'opens' || edge.relation === 'opens_direct') {
        linkTrustTwinPort(edge.source_id, portId, flowId, counts);
      }
      continue;
    }

    if (edge.relation === 'correlates') {
      const upstream = snapshot.edges.filter(
        (item) =>
          (item.relation === 'queries' || item.relation === 'queries_direct') &&
          item.target_id === edge.source_id,
      );
      if (upstream.length > 0) {
        for (const dnsEdge of upstream) {
          linkViaGateway(dnsEdge.source_id, portId, edgeCounts(dnsEdge));
        }
      } else {
        const opener = snapshot.edges.find(
          (item) =>
            (item.relation === 'opens' || item.relation === 'opens_direct') &&
            item.target_id === flowId,
        );
        if (opener) {
          linkViaGateway(opener.source_id, portId, counts);
        }
      }
    } else {
      linkViaGateway(edge.source_id, portId, counts);
    }

    upsertMapEdge(edgeMap, {
      source: portId,
      target: flowId,
      kind: 'port_to_flow',
      ...counts,
    });
  }

  for (const edge of snapshot.edges) {
    if (edge.relation !== 'runs') {
      continue;
    }
    // Only apps that talked to something (DNS/flow destinations).
    if (!activeApps.has(edge.target_id) && !flowParticipantIds.has(edge.target_id)) {
      continue;
    }
    ensureTwinNode(edge.source_id);
    ensureTwinNode(edge.target_id);
    upsertMapEdge(edgeMap, {
      source: edge.source_id,
      target: edge.target_id,
      kind: 'foreground',
      ...edgeCounts(edge),
    });
  }

  // TrustTwin egress: client → LAN → Internet (not host posture).
  for (const edge of snapshot.edges) {
    if (edge.relation !== 'routed_via') {
      continue;
    }
    const src = index.nodes.get(edge.source_id);
    const tgt = index.nodes.get(edge.target_id);
    const trustTwinPath =
      isTrustTwinDeviceId(edge.source_id) ||
      isTrustTwinNode(src) ||
      isTrustTwinNode(tgt);
    if (!trustTwinPath) {
      continue;
    }
    if (src?.entity_type === 'flow_session') {
      continue;
    }
    const tgtKind = String(tgt?.properties?.kind ?? '');
    if (tgtKind !== 'tt_lan' && edge.target_id !== PUBLIC_NETWORK_ID) {
      continue;
    }
    ensureTwinNode(edge.source_id);
    ensureTwinNode(edge.target_id);
    upsertMapEdge(edgeMap, {
      source: edge.source_id,
      target: edge.target_id,
      kind: edge.target_id === PUBLIC_NETWORK_ID ? 'path_tunnel' : 'path_egress',
      query_count: Math.max(1, Math.round(edge.weight)),
      blocked_count: 0,
    });
  }

  // Annotate Internet with public egress IP (no extra leaf node).
  for (const edge of snapshot.edges) {
    if (edge.relation !== 'destinates' || edge.source_id !== PUBLIC_NETWORK_ID) {
      continue;
    }
    const ipNode = index.nodes.get(edge.target_id);
    if (!ipNode || ipNode.entity_type !== 'ip_address' || !isTrustTwinNode(ipNode)) {
      continue;
    }
    const gateway = nodeMap.get(PUBLIC_NETWORK_ID);
    if (gateway) {
      nodeMap.set(PUBLIC_NETWORK_ID, {
        ...gateway,
        label: `Internet (${ipNode.label})`,
      });
    }
  }

  const connectedIds = new Set<string>();
  for (const edge of edgeMap.values()) {
    connectedIds.add(edge.source);
    connectedIds.add(edge.target);
  }
  for (const nodeId of [...nodeMap.keys()]) {
    if (connectedIds.has(nodeId)) {
      continue;
    }
    const node = nodeMap.get(nodeId);
    // Keep devices even without edges (TrustTwin heartbeat before first action_summary).
    if (node?.type === 'device') {
      continue;
    }
    nodeMap.delete(nodeId);
  }

  return {
    generated_at: snapshot.generated_at,
    minutes: snapshot.window_minutes,
    nodes: [...nodeMap.values()],
    edges: [...edgeMap.values()],
  };
}

export function projectTwinGraph(
  snapshot: TwinGraphSnapshot,
  mode: TwinProjectionMode,
  attributionOverride?: NetworkMapResponse | null,
): NetworkMapResponse {
  const attribution = projectAttributionGraph(snapshot, attributionOverride);
  if (mode === 'unified') {
    return projectUnifiedGraph(snapshot, attributionOverride);
  }
  if (mode === 'attribution') {
    return attribution;
  }
  if (mode === 'path') {
    return projectPathGraph(snapshot, attribution);
  }
  return projectFlowGraph(snapshot);
}
