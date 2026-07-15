import { NetworkMapEdge, NetworkMapNode } from '../types/networkMap';
import { aggregateFlowDestinations } from './aggregateFlowDestinations';

function buildFlowGraph(flowCount: number): { nodes: NetworkMapNode[]; edges: NetworkMapEdge[] } {
  const nodes: NetworkMapNode[] = [
    { id: 'port:443', type: 'port', label: '443' },
  ];
  const edges: NetworkMapEdge[] = [];
  for (let i = 0; i < flowCount; i += 1) {
    const id = `flow:tcp:1.2.3.${i}:443:10.0.0.1`;
    nodes.push({ id, type: 'flow', label: `1.2.3.${i}` });
    edges.push({
      source: 'port:443',
      target: id,
      kind: 'port_to_flow',
      query_count: 1,
      blocked_count: 0,
    });
  }
  return { nodes, edges };
}

describe('aggregateFlowDestinations', () => {
  it('collapses many flows into one summary node by default', () => {
    const { nodes, edges } = buildFlowGraph(12);
    const result = aggregateFlowDestinations(nodes, edges);
    expect(result.nodes.filter((n) => n.type === 'flow')).toHaveLength(0);
    expect(result.nodes.some((n) => n.type === 'flow_summary' && n.label === '12 connections on 443')).toBe(true);
    expect(result.edges.filter((e) => e.kind === 'port_to_flow')).toHaveLength(1);
  });

  it('aggregates gateway sessions when no port hubs exist', () => {
    const nodes = [
      { id: 'infra:dns_resolver', type: 'gateway' as const, label: 'EC2 DNS' },
    ];
    const edges: NetworkMapEdge[] = [];
    for (let i = 0; i < 8; i += 1) {
      const id = `flow:tcp:1.2.3.${i}:443:10.0.0.1`;
      nodes.push({ id, type: 'flow', label: `1.2.3.${i}:443` });
      edges.push({
        source: 'infra:dns_resolver',
        target: id,
        kind: 'gateway_to_flow',
        query_count: 1,
        blocked_count: 0,
      });
    }
    const result = aggregateFlowDestinations(nodes, edges);
    expect(result.nodes.filter((n) => n.type === 'flow')).toHaveLength(0);
    expect(result.nodes.some((n) => n.type === 'flow_summary' && n.label === '8 live sessions')).toBe(true);
  });

  it('shows top five plus more node in partial expansion', () => {
    const { nodes, edges } = buildFlowGraph(8);
    const result = aggregateFlowDestinations(nodes, edges, { 443: 'partial' });
    expect(result.nodes.filter((n) => n.type === 'flow')).toHaveLength(5);
    expect(result.nodes.some((n) => n.type === 'flow_more' && n.label === '+3 more')).toBe(true);
  });

  it('shows all flows when expanded to full', () => {
    const { nodes, edges } = buildFlowGraph(8);
    const result = aggregateFlowDestinations(nodes, edges, { 443: 'full' });
    expect(result.nodes.filter((n) => n.type === 'flow')).toHaveLength(8);
  });
});
