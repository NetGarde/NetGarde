import { NetworkMapEdge } from '../types/networkMap';
import { edgeKey } from './whatIfSimulation';

export const EC2_GATEWAY_NODE_ID = 'infra:ec2_gateway';
export const DNS_GATEWAY_NODE_ID = 'infra:dns_resolver';

export interface TunnelWhatIfSimulationResult {
  tunnelBlocked: boolean;
  gatewayBlocked: boolean;
  disabledEdgeKeys: Set<string>;
  affectedPathCount: number;
}

/** Simulate EC2 gateway or EC2 DNS resolver failure. */
export function computeTunnelWhatIfSimulation(
  edges: NetworkMapEdge[],
  tunnelBlocked: boolean,
  gatewayBlocked: boolean,
): TunnelWhatIfSimulationResult {
  const disabledEdgeKeys = new Set<string>();
  let affectedPathCount = 0;

  if (!tunnelBlocked && !gatewayBlocked) {
    return { tunnelBlocked, gatewayBlocked, disabledEdgeKeys, affectedPathCount: 0 };
  }

  for (const edge of edges) {
    let cut = false;

    if (tunnelBlocked) {
      if (edge.source === EC2_GATEWAY_NODE_ID || edge.target === EC2_GATEWAY_NODE_ID) {
        cut = true;
      }
      if (edge.kind === 'flow_via_gateway') {
        cut = true;
      }
    }

    if (gatewayBlocked) {
      if (edge.source === DNS_GATEWAY_NODE_ID || edge.target === DNS_GATEWAY_NODE_ID) {
        cut = true;
      }
      if (edge.kind === 'to_port' || edge.kind === 'port_to_flow') {
        cut = true;
      }
    }

    if (cut) {
      disabledEdgeKeys.add(edgeKey(edge));
      affectedPathCount += Math.max(1, edge.query_count);
    }
  }

  return { tunnelBlocked, gatewayBlocked, disabledEdgeKeys, affectedPathCount };
}
