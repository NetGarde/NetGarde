import {
  buildDestinationRows,
  filterGraphByClient,
  focusPathGraph,
} from './buildDestinationRows';
import { NetworkMapResponse } from '../types/networkMap';

const sampleGraph: NetworkMapResponse = {
  generated_at: '2026-07-04T00:00:00Z',
  minutes: 15,
  nodes: [
    { id: 'device:1', type: 'device', label: 'laptop', client_ip: '10.0.0.12' },
    { id: 'device:twin:a', type: 'device', label: 'mbp', client_ip: '203.0.113.10' },
    { id: 'app:slack', type: 'app', label: 'Slack', app_slug: 'slack' },
    { id: 'domain:api.slack.com', type: 'domain', label: 'api.slack.com', blocked: false },
    { id: 'domain:bad.example', type: 'domain', label: 'bad.example', blocked: true },
    { id: 'infra:tt:a:tt_lan', type: 'tunnel', label: 'Wi‑Fi' },
    { id: 'infra:public_network', type: 'gateway', label: 'Internet (203.0.113.10)' },
    { id: 'port:tcp:443', type: 'port', label: 'HTTPS :443' },
    {
      id: 'flow:1',
      type: 'flow',
      label: 'Safari · HTTPS ×28',
      process_name: 'Safari',
      app_slug: 'com-apple-safari',
    },
  ],
  edges: [
    { source: 'device:1', target: 'app:slack', kind: 'foreground', query_count: 1, blocked_count: 0 },
    { source: 'app:slack', target: 'domain:api.slack.com', kind: 'dns', query_count: 4, blocked_count: 0 },
    { source: 'app:slack', target: 'domain:bad.example', kind: 'dns', query_count: 1, blocked_count: 1 },
    { source: 'device:twin:a', target: 'infra:tt:a:tt_lan', kind: 'path_egress', query_count: 1, blocked_count: 0 },
    { source: 'infra:tt:a:tt_lan', target: 'infra:public_network', kind: 'path_tunnel', query_count: 1, blocked_count: 0 },
    { source: 'infra:public_network', target: 'port:tcp:443', kind: 'to_port', query_count: 28, blocked_count: 0 },
    { source: 'port:tcp:443', target: 'flow:1', kind: 'port_to_flow', query_count: 28, blocked_count: 0 },
  ],
};

describe('buildDestinationRows', () => {
  it('builds DNS and session rows with block action first', () => {
    const rows = buildDestinationRows(sampleGraph);
    expect(rows.some((r) => r.destination === 'bad.example' && r.action === 'block')).toBe(true);
    expect(rows.some((r) => r.destination === 'api.slack.com' && r.appLabel === 'Slack')).toBe(true);
    expect(rows.some((r) => r.clientLabel === 'mbp' && r.port === '443' && r.appLabel === 'Safari')).toBe(
      true,
    );
    // Grouped by client: all rows for a client are contiguous; blocked first within client.
    const laptopRows = rows.filter((r) => r.clientLabel === 'laptop');
    expect(laptopRows[0].action).toBe('block');
    expect(laptopRows.some((r) => r.appLabel === 'Slack')).toBe(true);
  });
});

describe('filterGraphByClient', () => {
  it('scopes graph to one client', () => {
    const scoped = filterGraphByClient(sampleGraph, 'device:1');
    expect(scoped.nodes.some((n) => n.id === 'device:1')).toBe(true);
    expect(scoped.nodes.some((n) => n.id === 'device:twin:a')).toBe(false);
    expect(scoped.nodes.some((n) => n.id === 'domain:api.slack.com')).toBe(true);
  });
});

describe('focusPathGraph', () => {
  it('shows only egress spine for TrustTwin by default', () => {
    const focused = focusPathGraph(sampleGraph, 'device:twin:a', null);
    expect(focused.nodes.some((n) => n.id === 'device:twin:a')).toBe(true);
    expect(focused.nodes.some((n) => n.type === 'tunnel')).toBe(true);
    expect(focused.nodes.some((n) => n.type === 'gateway')).toBe(true);
    expect(focused.nodes.some((n) => n.type === 'port')).toBe(false);
    expect(focused.nodes.some((n) => n.type === 'flow')).toBe(false);
  });

  it('expands one TrustTwin port when a session row is selected', () => {
    const rows = buildDestinationRows(sampleGraph);
    const sessionRow = rows.find((r) => r.clientId === 'device:twin:a' && r.port === '443');
    expect(sessionRow).toBeTruthy();
    const focused = focusPathGraph(sampleGraph, 'device:twin:a', sessionRow!);
    expect(focused.nodes.some((n) => n.type === 'port')).toBe(true);
    expect(focused.nodes.some((n) => n.id === 'flow:1')).toBe(true);
    expect(focused.nodes.filter((n) => n.type === 'port')).toHaveLength(1);
  });

  it('shows endpoint domains by default but not session pins', () => {
    const focused = focusPathGraph(sampleGraph, 'device:1', null);
    expect(focused.nodes.some((n) => n.id === 'domain:api.slack.com')).toBe(true);
    expect(focused.nodes.some((n) => n.type === 'app')).toBe(true);
    expect(focused.nodes.some((n) => n.type === 'flow')).toBe(false);
  });
});
