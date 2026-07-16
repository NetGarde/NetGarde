import {
  projectAttributionGraph,
  projectFlowGraph,
  projectPathGraph,
  projectTwinGraph,
  projectUnifiedGraph,
} from './projectGraph';
import { TwinGraphIndex } from '../graph/TwinGraphIndex';
import { TwinGraphSnapshot } from '../types/twinGraph';

function sampleSnapshot(): TwinGraphSnapshot {
  return {
    generated_at: '2026-01-01T00:00:00Z',
    window_minutes: 15,
    nodes: [
      {
        id: 'device:1',
        entity_type: 'device',
        layer: 'observed',
        label: 'laptop',
        properties: { client_ip: '10.0.0.12', device_id: 1, fresh: true },
      },
      {
        id: 'app:zoom',
        entity_type: 'app',
        layer: 'observed',
        label: 'Zoom',
        properties: { app_slug: 'zoom' },
      },
      {
        id: 'domain:zoom.us',
        entity_type: 'domain',
        layer: 'observed',
        label: 'zoom.us',
        properties: { blocked: false },
      },
      {
        id: 'infra:ec2_gateway',
        entity_type: 'infra_component',
        layer: 'desired',
        label: 'EC2 Gateway',
        properties: { kind: 'ec2_gateway' },
      },
      {
        id: 'infra:dns_resolver',
        entity_type: 'infra_component',
        layer: 'desired',
        label: 'TrustEdge DNS',
        properties: { kind: 'dns_resolver' },
      },
      {
        id: 'l4:tcp:443',
        entity_type: 'l4_service',
        layer: 'observed',
        label: 'TCP 443',
        properties: { protocol: 'tcp', port: 443 },
      },
      {
        id: 'flow:tcp:93.184.216.34:443:10.0.0.12',
        entity_type: 'flow_session',
        layer: 'observed',
        label: 'TCP/443',
        properties: { protocol: 'tcp', dest_ip: '93.184.216.34', dest_port: 443, client_ip: '10.0.0.12' },
      },
      {
        id: 'ip:93.184.216.34',
        entity_type: 'ip_address',
        layer: 'observed',
        label: '93.184.216.34',
        properties: { addr: '93.184.216.34' },
      },
    ],
    edges: [
      {
        id: 'runs:device:1->app:zoom',
        source_id: 'device:1',
        target_id: 'app:zoom',
        relation: 'runs',
        layer: 'observed',
        weight: 1,
        properties: {},
      },
      {
        id: 'queries:app:zoom->domain:zoom.us',
        source_id: 'app:zoom',
        target_id: 'domain:zoom.us',
        relation: 'queries',
        layer: 'observed',
        weight: 3,
        properties: { blocked_count: 0 },
      },
      {
        id: 'opens:app:zoom->flow:tcp:93.184.216.34:443:10.0.0.12',
        source_id: 'app:zoom',
        target_id: 'flow:tcp:93.184.216.34:443:10.0.0.12',
        relation: 'opens',
        layer: 'observed',
        weight: 1,
        properties: {},
      },
      {
        id: 'uses:flow->l4',
        source_id: 'flow:tcp:93.184.216.34:443:10.0.0.12',
        target_id: 'l4:tcp:443',
        relation: 'uses_service',
        layer: 'observed',
        weight: 1,
        properties: {},
      },
      {
        id: 'dest:flow->ip',
        source_id: 'flow:tcp:93.184.216.34:443:10.0.0.12',
        target_id: 'ip:93.184.216.34',
        relation: 'destinates',
        layer: 'observed',
        weight: 1,
        properties: {},
      },
    ],
  };
}

describe('projectAttributionGraph', () => {
  it('maps observed telemetry to attribution nodes and edges', () => {
    const result = projectAttributionGraph(sampleSnapshot());
    expect(result.nodes.map((n) => n.type).sort()).toEqual(['app', 'device', 'domain']);
    expect(result.edges.some((e) => e.kind === 'foreground')).toBe(true);
    expect(result.edges.some((e) => e.kind === 'dns')).toBe(true);
  });
});

describe('projectPathGraph', () => {
  it('includes infra nodes from twin graph', () => {
    const attribution = projectAttributionGraph(sampleSnapshot());
    const result = projectPathGraph(sampleSnapshot(), attribution);
    const types = new Set(result.nodes.map((n) => n.type));
    expect(types.has('tunnel')).toBe(true);
    expect(types.has('gateway')).toBe(true);
    expect(result.edges.some((e) => e.kind === 'path_egress')).toBe(true);
    expect(result.edges.some((e) => e.kind === 'path_tunnel')).toBe(true);
  });
});

describe('projectFlowGraph', () => {
  it('projects flow sessions to port hubs', () => {
    const result = projectFlowGraph(sampleSnapshot());
    expect(result.nodes.some((n) => n.type === 'port' && n.label === '443')).toBe(true);
    expect(result.nodes.some((n) => n.type === 'flow')).toBe(true);
    expect(result.edges.some((e) => e.kind === 'port_to_flow')).toBe(true);
  });

  it('routes uncorrelated flows through EC2 DNS gateway', () => {
    const result = projectFlowGraph(sampleSnapshot());
    expect(result.edges.some((e) => e.kind === 'flow_via_gateway' && e.target === 'infra:dns_resolver')).toBe(true);
    expect(result.edges.some((e) => e.kind === 'to_port' && e.source === 'infra:dns_resolver')).toBe(true);
    expect(result.nodes.some((n) => n.type === 'gateway' && n.label === 'EC2 DNS')).toBe(true);
  });

  it('drops enrolled devices with no live flows', () => {
    const snapshot: TwinGraphSnapshot = {
      ...sampleSnapshot(),
      nodes: [
        ...sampleSnapshot().nodes,
        {
          id: 'device:99',
          entity_type: 'device',
          layer: 'observed',
          label: 'old-laptop',
          properties: { client_ip: '10.0.0.99', device_id: 99, fresh: false },
        },
      ],
    };
    const result = projectFlowGraph(snapshot);
    expect(result.nodes.some((n) => n.id === 'device:99')).toBe(false);
    expect(result.nodes.some((n) => n.id === 'device:1')).toBe(true);
  });
});

describe('projectUnifiedGraph', () => {
  it('includes DNS path, ports, flows, and infra without policy gates', () => {
    const result = projectUnifiedGraph(sampleSnapshot());
    const types = new Set(result.nodes.map((n) => n.type));
    expect(types.has('tunnel')).toBe(true);
    expect(types.has('gateway')).toBe(true);
    expect(types.has('flow')).toBe(true);
    expect(types.has('policy')).toBe(false);
    expect(result.nodes.some((n) => n.type === 'port' && n.label === '443')).toBe(true);
    expect(result.edges.some((e) => e.kind === 'path_egress')).toBe(true);
    expect(result.edges.some((e) => e.kind === 'port_to_flow')).toBe(true);
    expect(result.edges.some((e) => e.kind === 'dns')).toBe(true);
  });

  it('drops TrustTwin focus apps that have no destinations', () => {
    const snapshot: TwinGraphSnapshot = {
      generated_at: '2026-07-04T00:00:00Z',
      window_minutes: 1,
      nodes: [
        {
          id: 'device:twin:dev_mbp',
          entity_type: 'device',
          layer: 'observed',
          label: 'elad-mbp',
          properties: {
            source: 'trusttwin',
            device_id: 'dev_mbp',
            public_ip: '203.0.113.10',
          },
        },
        {
          id: 'app:com-microsoft-vscode',
          entity_type: 'app',
          layer: 'observed',
          label: 'Code',
          properties: { source: 'trusttwin', app_slug: 'com-microsoft-vscode' },
        },
      ],
      edges: [
        {
          id: 'runs:device:twin:dev_mbp->app:com-microsoft-vscode',
          source_id: 'device:twin:dev_mbp',
          target_id: 'app:com-microsoft-vscode',
          relation: 'runs',
          layer: 'observed',
          weight: 55,
          properties: { duration_sec: 55 },
        },
      ],
    };
    const result = projectUnifiedGraph(snapshot);
    expect(result.nodes.some((n) => n.id === 'device:twin:dev_mbp')).toBe(true);
    expect(result.nodes.some((n) => n.id === 'app:com-microsoft-vscode')).toBe(false);
    expect(result.edges.some((e) => e.kind === 'foreground')).toBe(false);
    expect(result.nodes.find((n) => n.id === 'device:twin:dev_mbp')?.client_ip).toBe('203.0.113.10');
  });

  it('projects TrustTwin path: client → LAN → Internet → remote ports', () => {
    const snapshot: TwinGraphSnapshot = {
      generated_at: '2026-07-04T00:00:00Z',
      window_minutes: 1,
      nodes: [
        {
          id: 'device:twin:dev_mbp',
          entity_type: 'device',
          layer: 'observed',
          label: 'elad-mbp',
          properties: {
            source: 'trusttwin',
            device_id: 'dev_mbp',
            public_ip: '203.0.113.10',
            client_ip: '203.0.113.10',
          },
        },
        {
          id: 'infra:tt:dev_mbp:tt_lan',
          entity_type: 'infra_component',
          layer: 'observed',
          label: 'Wi‑Fi',
          properties: { kind: 'tt_lan', source: 'trusttwin' },
        },
        {
          id: 'infra:public_network',
          entity_type: 'infra_component',
          layer: 'observed',
          label: 'Internet',
          properties: { kind: 'public_network', source: 'trusttwin' },
        },
        {
          id: 'ip:203.0.113.10',
          entity_type: 'ip_address',
          layer: 'observed',
          label: '203.0.113.10',
          properties: { source: 'trusttwin', role: 'public_egress', addr: '203.0.113.10' },
        },
        {
          id: 'l4:tcp:443',
          entity_type: 'l4_service',
          layer: 'observed',
          label: 'HTTPS :443',
          properties: { protocol: 'tcp', port: 443, service: 'HTTPS', source: 'trusttwin' },
        },
        {
          id: 'flow:tcp:agg:443:203.0.113.10',
          entity_type: 'flow_session',
          layer: 'observed',
          label: 'HTTPS ×28',
          properties: {
            protocol: 'tcp',
            dest_ip: '*',
            dest_port: 443,
            client_ip: '203.0.113.10',
            source: 'trusttwin',
            aggregate: true,
            service: 'HTTPS',
          },
        },
      ],
      edges: [
        {
          id: 'routed_via:device:twin:dev_mbp->infra:tt:dev_mbp:tt_lan',
          source_id: 'device:twin:dev_mbp',
          target_id: 'infra:tt:dev_mbp:tt_lan',
          relation: 'routed_via',
          layer: 'observed',
          weight: 1,
          properties: { source: 'trusttwin' },
        },
        {
          id: 'routed_via:infra:tt:dev_mbp:tt_lan->infra:public_network',
          source_id: 'infra:tt:dev_mbp:tt_lan',
          target_id: 'infra:public_network',
          relation: 'routed_via',
          layer: 'observed',
          weight: 1,
          properties: { source: 'trusttwin' },
        },
        {
          id: 'destinates:infra:public_network->ip:203.0.113.10',
          source_id: 'infra:public_network',
          target_id: 'ip:203.0.113.10',
          relation: 'destinates',
          layer: 'observed',
          weight: 1,
          properties: { source: 'trusttwin' },
        },
        {
          id: 'opens_direct:infra:public_network->flow:tcp:agg:443:203.0.113.10',
          source_id: 'infra:public_network',
          target_id: 'flow:tcp:agg:443:203.0.113.10',
          relation: 'opens_direct',
          layer: 'observed',
          weight: 28,
          properties: { source: 'trusttwin' },
        },
        {
          id: 'uses_service:flow:tcp:agg:443:203.0.113.10->l4:tcp:443',
          source_id: 'flow:tcp:agg:443:203.0.113.10',
          target_id: 'l4:tcp:443',
          relation: 'uses_service',
          layer: 'observed',
          weight: 28,
          properties: { source: 'trusttwin' },
        },
      ],
    };
    const result = projectUnifiedGraph(snapshot);
    expect(result.nodes.some((n) => n.id === 'device:twin:dev_mbp')).toBe(true);
    expect(result.nodes.some((n) => n.type === 'tunnel' && n.label === 'Wi‑Fi')).toBe(true);
    expect(result.nodes.some((n) => n.type === 'gateway' && n.label.includes('Internet'))).toBe(true);
    expect(result.nodes.some((n) => n.type === 'gateway' && n.label.includes('203.0.113.10'))).toBe(true);
    expect(result.nodes.some((n) => n.type === 'port' && n.label.includes('443'))).toBe(true);
    expect(result.nodes.some((n) => n.type === 'flow' && n.label.includes('HTTPS'))).toBe(true);
    // Ports hang off Internet, not the client.
    expect(
      result.edges.some(
        (e) => e.kind === 'to_port' && e.source === 'infra:public_network' && e.target.includes('443'),
      ),
    ).toBe(true);
    expect(
      result.edges.some((e) => e.kind === 'to_port' && e.source === 'device:twin:dev_mbp'),
    ).toBe(false);
    expect(result.edges.some((e) => e.kind === 'path_egress')).toBe(true);
    expect(result.edges.some((e) => e.kind === 'path_tunnel')).toBe(true);
    expect(result.edges.some((e) => e.kind === 'port_to_flow')).toBe(true);
    expect(result.edges.some((e) => e.kind === 'flow_via_gateway')).toBe(false);
  });

  it('keeps TrustTwin devices with no focus apps yet', () => {
    const snapshot: TwinGraphSnapshot = {
      generated_at: '2026-07-04T00:00:00Z',
      window_minutes: 1,
      nodes: [
        {
          id: 'device:twin:dev_idle',
          entity_type: 'device',
          layer: 'observed',
          label: 'idle-mac',
          properties: { source: 'trusttwin', device_id: 'dev_idle' },
        },
      ],
      edges: [],
    };
    const result = projectUnifiedGraph(snapshot);
    expect(result.nodes.some((n) => n.id === 'device:twin:dev_idle')).toBe(true);
  });
});

describe('projectTwinGraph', () => {
  it('selects projection by mode', () => {
    const snapshot = sampleSnapshot();
    expect(projectTwinGraph(snapshot, 'attribution').edges.some((e) => e.kind === 'dns')).toBe(true);
    expect(projectTwinGraph(snapshot, 'path').edges.some((e) => e.kind === 'path_egress')).toBe(true);
    expect(projectTwinGraph(snapshot, 'flow').nodes.some((n) => n.type === 'port')).toBe(true);
    expect(projectTwinGraph(snapshot, 'unified').nodes.some((n) => n.type === 'port')).toBe(true);
  });
});

describe('TwinGraphIndex', () => {
  it('traverses reverse from domain to device', () => {
    const index = new TwinGraphIndex(sampleSnapshot());
    const result = index.traverse({
      seed_node_ids: ['domain:zoom.us'],
      direction: 'in',
      relations: ['queries', 'runs', 'assigned'],
      max_depth: 4,
      layers: ['observed', 'desired'],
    });
    expect(result.nodes.some((n) => n.id === 'device:1')).toBe(true);
  });
});
