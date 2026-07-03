import { NetworkMapEdge } from '../types/networkMap';
import {
  computeTunnelWhatIfSimulation,
  DNS_GATEWAY_NODE_ID,
  WIREGUARD_NODE_ID,
} from './tunnelWhatIfSimulation';

const edges: NetworkMapEdge[] = [
  { source: 'app:chrome', target: WIREGUARD_NODE_ID, kind: 'path_egress', query_count: 2, blocked_count: 0 },
  { source: WIREGUARD_NODE_ID, target: DNS_GATEWAY_NODE_ID, kind: 'path_tunnel', query_count: 2, blocked_count: 0 },
  { source: DNS_GATEWAY_NODE_ID, target: 'port:443', kind: 'to_port', query_count: 1, blocked_count: 0 },
  { source: 'port:443', target: 'flow:1', kind: 'port_to_flow', query_count: 1, blocked_count: 0 },
  { source: DNS_GATEWAY_NODE_ID, target: 'domain:github.com', kind: 'flow_via_gateway', query_count: 3, blocked_count: 0 },
];

describe('computeTunnelWhatIfSimulation', () => {
  it('cuts wireguard and flow_via_gateway edges when tunnel is blocked', () => {
    const result = computeTunnelWhatIfSimulation(edges, true, false);
    expect(result.tunnelBlocked).toBe(true);
    expect(result.disabledEdgeKeys.size).toBe(3);
    expect(result.affectedPathCount).toBeGreaterThan(0);
  });

  it('cuts gateway port paths when gateway is blocked', () => {
    const result = computeTunnelWhatIfSimulation(edges, false, true);
    expect(result.gatewayBlocked).toBe(true);
    expect(result.disabledEdgeKeys.size).toBe(4);
  });

  it('returns no cuts when infra is healthy', () => {
    const result = computeTunnelWhatIfSimulation(edges, false, false);
    expect(result.disabledEdgeKeys.size).toBe(0);
    expect(result.affectedPathCount).toBe(0);
  });
});
