import { useEffect, useMemo, useState } from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Paper from '@mui/material/Paper';
import Stack from '@mui/material/Stack';
import Chip from '@mui/material/Chip';
import CircularProgress from '@mui/material/CircularProgress';
import Alert from '@mui/material/Alert';
import Button from '@mui/material/Button';
import Switch from '@mui/material/Switch';
import FormControlLabel from '@mui/material/FormControlLabel';
import FormControl from '@mui/material/FormControl';
import InputLabel from '@mui/material/InputLabel';
import MenuItem from '@mui/material/MenuItem';
import Select from '@mui/material/Select';
import { alpha, useTheme } from '@mui/material/styles';
import HubIcon from '@mui/icons-material/Hub';
import ScienceIcon from '@mui/icons-material/Science';
import BlockIcon from '@mui/icons-material/Block';
import ScatterPlotIcon from '@mui/icons-material/ScatterPlot';
import DestinationTable from './DestinationTable';
import {
  buildDestinationRows,
  DestinationRow,
  focusPathGraph,
  listClientsFromRows,
} from '../utils/buildDestinationRows';
import { useTwinGraph } from '../../twin-graph/hooks/useTwinGraph';
import { SimulationCommandResponse } from '../../twin-graph/api/twinGraphApi';
import { projectTwinGraph } from '../../twin-graph/projections/projectGraph';
import { DEFAULT_NETWORK_MAP_MINUTES } from '../config/api';
import {
  edgePath,
  layoutNetworkMap,
  NetworkMapLayoutStyle,
  pathColumnLabels,
  shortenLabel,
} from '../utils/layoutNetworkMap';
import { layoutForceDirected } from '../utils/layoutForceDirected';
import { flowNodeTooltip, parseFlowNode, parsePortLabel, portNodeTooltip } from '../utils/flowLabels';
import {
  computePortWhatIfSimulation,
  listActivePortNumbers,
  PortWhatIfSimulationResult,
  toggleDisabledPortNumber,
} from '../utils/portWhatIfSimulation';
import {
  computeTunnelWhatIfSimulation,
  TunnelWhatIfSimulationResult,
} from '../utils/tunnelWhatIfSimulation';
import {
  aggregateFlowDestinations,
  nextPortDestExpansion,
  parseAggregateHubFromNode,
  parseAggregatePortFromNode,
  PortDestExpansion,
} from '../utils/aggregateFlowDestinations';
import { getNodeIconStyle } from '../utils/appIcons';
import {
  estimateBadgeWidth,
  formatPinLabel,
  getNodeVisualSpec,
  GRAPH_BADGE,
} from '../utils/graphVisual';
import { NetworkMapEdge, NetworkMapNode, PositionedNode } from '../types/networkMap';
import {
  computeWhatIfSimulation,
  edgeKey,
  toggleDisabledApp,
  WhatIfSimulationResult,
} from '../utils/whatIfSimulation';
import {
  buildPathFlowDetailsForDomain,
  PathFlowDetail,
} from '../utils/buildPathFlowDetail';
import PathFlowDetailPanel from './PathFlowDetailPanel';
import SimulationCommandBar from './SimulationCommandBar';

interface MapNodeGlyphProps {
  node: PositionedNode;
  whatIfMode: boolean;
  portDisabled: boolean;
  infraDisabled: boolean;
  appDisabled: boolean;
  simulatedBlocked: boolean;
  selected: boolean;
  onSelectApp?: (nodeId: string) => void;
  onSelectDomain?: (nodeId: string) => void;
  onSelectPort?: (port: number) => void;
  onSelectTunnel?: () => void;
  onSelectGateway?: () => void;
  onExpandFlowAggregate?: (node: NetworkMapNode) => void;
}

function MapNodeGlyph({
  node,
  whatIfMode,
  portDisabled,
  infraDisabled,
  appDisabled,
  simulatedBlocked,
  selected,
  onSelectApp,
  onSelectDomain,
  onSelectPort,
  onSelectTunnel,
  onSelectGateway,
  onExpandFlowAggregate,
}: MapNodeGlyphProps) {
  const theme = useTheme();
  const style = getNodeIconStyle({
    type: node.type,
    app_slug: node.app_slug,
    blocked: node.blocked || simulatedBlocked,
    label: node.label,
  });
  const visual = getNodeVisualSpec(node.type);
  const nodeR = visual.radius;
  const iconSize = visual.iconSize;

  const isInfra = node.type === 'tunnel' || node.type === 'gateway' || node.type === 'policy';
  const isLanTunnel =
    node.type === 'tunnel' && /wi-?fi|ethernet|cellular|network/i.test(node.label);

  const ring = appDisabled || portDisabled || infraDisabled
    ? theme.palette.error.main
    : selected
      ? theme.palette.text.primary
      : node.type === 'domain' && (node.blocked || simulatedBlocked)
        ? theme.palette.error.main
        : alpha(theme.palette.text.primary, 0.35);

  const tooltipParts = [
    node.type === 'app'
      ? `${node.label} (process with network activity)`
      : node.type === 'domain'
        ? `${node.label}${node.blocked ? ' · blocked' : ''}${simulatedBlocked ? ' · would lose access (what-if)' : ''}`
        : node.type === 'flow'
          ? (() => {
              const parsed = parseFlowNode(node);
              return parsed
                ? `${parsed.protocol.toUpperCase()}/${parsed.port} · ${node.label}`
                : flowNodeTooltip(node.label);
            })()
          : node.type === 'flow_summary'
            ? `${node.label} · click to expand destinations`
            : node.type === 'flow_more'
              ? `${node.label} · click to show all destinations`
          : node.type === 'port'
            ? (() => {
                const portNum = Number(String(node.label).replace(/.*:/, ''));
                return Number.isFinite(portNum)
                  ? portNodeTooltip(portNum)
                  : `${node.label} · remote service port`;
              })()
          : node.type === 'gateway'
            ? node.label.toLowerCase().startsWith('internet')
              ? `${node.label} · public egress path`
              : `${node.label} · DNS resolver`
          : node.type === 'tunnel'
            ? isLanTunnel
              ? `${node.label} · local network link`
              : `${node.label} · EC2 gateway`
              : `${node.label}${node.client_ip ? ` · ${node.client_ip}` : ''}`,
  ];
  if (whatIfMode && node.type === 'app') {
    tooltipParts.push(appDisabled ? 'Click to re-enable in what-if' : 'Click to disable in what-if');
  }
  if (whatIfMode && node.type === 'port') {
    tooltipParts.push(portDisabled ? 'Click to unblock in what-if' : 'Click to simulate blocking this port');
  }
  if (whatIfMode && node.type === 'tunnel' && !isLanTunnel) {
    tooltipParts.push(infraDisabled ? 'Click to restore gateway in what-if' : 'Click to simulate EC2 gateway down');
  }
  if (whatIfMode && node.type === 'gateway') {
    tooltipParts.push(infraDisabled ? 'Click to restore DNS in what-if' : 'Click to simulate EC2 DNS failure');
  }
  if (node.type === 'domain') {
    tooltipParts.push('Click to inspect DNS path');
  }

  const selectableApp = whatIfMode && node.type === 'app';
  const selectablePort = whatIfMode && node.type === 'port';
  const selectableTunnel = whatIfMode && node.type === 'tunnel' && !isLanTunnel;
  const selectableGateway = whatIfMode && node.type === 'gateway';
  const selectableDomain = node.type === 'domain';
  const expandableAggregate = node.type === 'flow_summary' || node.type === 'flow_more';
  const disabledVisual = appDisabled || portDisabled || infraDisabled;
  const pinLabel = formatPinLabel(node);
  const showBadge = visual.showBadge && pinLabel != null;
  const badgeWidth = showBadge ? estimateBadgeWidth(pinLabel!, visual.badgeMonospace) : 0;
  const badgeY = nodeR + GRAPH_BADGE.offsetY;

  return (
    <g
      transform={`translate(${node.x}, ${node.y})`}
      style={{
        cursor:
          selectableApp ||
          selectableDomain ||
          selectablePort ||
          selectableTunnel ||
          selectableGateway ||
          expandableAggregate
            ? 'pointer'
            : 'default',
        opacity: disabledVisual ? 0.45 : 1,
      }}
      onClick={
        selectableApp
          ? () => onSelectApp?.(node.id)
          : selectableDomain
            ? () => onSelectDomain?.(node.id)
            : selectablePort
              ? () => {
                  const port = parsePortLabel(node.label);
                  if (port != null) {
                    onSelectPort?.(port);
                  }
                }
              : selectableTunnel
                ? () => onSelectTunnel?.()
                : selectableGateway
                  ? () => onSelectGateway?.()
                  : expandableAggregate
                    ? () => onExpandFlowAggregate?.(node)
                    : undefined
      }
    >
      <title>{tooltipParts.join(' · ')}</title>
      <circle
        r={nodeR}
        fill={theme.palette.background.paper}
        stroke={ring}
        strokeWidth={selected || disabledVisual ? 1.5 : 1}
        strokeDasharray={disabledVisual ? '3 2' : undefined}
      />
      <circle
        r={nodeR - 1}
        fill={style.bg}
        stroke={alpha(theme.palette.divider, 0.9)}
        strokeWidth={1}
      />
      {isInfra && (
        <circle
          r={nodeR - 4}
          fill="none"
          stroke={alpha(theme.palette.divider, 0.6)}
          strokeWidth={1}
        />
      )}
      {(appDisabled || infraDisabled) && (
        <line
          x1={-nodeR}
          y1={-nodeR}
          x2={nodeR}
          y2={nodeR}
          stroke={theme.palette.error.main}
          strokeWidth={2}
        />
      )}
      <foreignObject
        x={-iconSize / 2}
        y={-iconSize / 2}
        width={iconSize}
        height={iconSize}
        style={{ pointerEvents: 'none' }}
      >
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: style.color,
            fontSize: iconSize,
            width: iconSize,
            height: iconSize,
            '& svg': { fontSize: iconSize },
          }}
        >
          {style.icon}
        </Box>
      </foreignObject>
      {showBadge && (
        <>
          <rect
            x={-badgeWidth / 2}
            y={badgeY}
            width={badgeWidth}
            height={GRAPH_BADGE.height}
            rx={GRAPH_BADGE.rx}
            fill={theme.palette.background.paper}
            stroke={theme.palette.divider}
            strokeWidth={1}
          />
          <text
            y={badgeY + GRAPH_BADGE.height / 2 + 3.5}
            textAnchor="middle"
            fontSize={GRAPH_BADGE.fontSize}
            fontWeight={GRAPH_BADGE.fontWeight}
            fill={theme.palette.text.secondary}
            style={{ fontFamily: visual.badgeMonospace ? 'ui-monospace, SFMono-Regular, Menlo, monospace' : undefined }}
          >
            {pinLabel}
          </text>
        </>
      )}
    </g>
  );
}

function edgeTooltip(
  edge: NetworkMapEdge,
  nodes: Map<string, PositionedNode>,
  simulatedCut: boolean,
): string {
  const source = nodes.get(edge.source)?.label ?? edge.source;
  const target = nodes.get(edge.target)?.label ?? edge.target;
  if (simulatedCut) {
    return `${source} → ${target} · cut by what-if`;
  }
  if (edge.kind === 'foreground') {
    return `${source} → ${target} (foreground app)`;
  }
  if (edge.kind === 'path_egress') {
    return `${source} → ${target} · DNS leaves endpoint via EC2 gateway (${edge.query_count} quer${edge.query_count === 1 ? 'y' : 'ies'})`;
  }
  if (edge.kind === 'path_tunnel') {
    return `${source} → ${target} · gateway transit`;
  }
  if (edge.kind === 'path_resolve') {
    return `${source} → ${target} · query received by dnsmasq`;
  }
  if (edge.kind === 'path_forward') {
    const blocked = edge.blocked_count > 0 ? ` · ${edge.blocked_count} blocked` : '';
    return `${source} → ${target} · policy decision · ${edge.query_count} quer${edge.query_count === 1 ? 'y' : 'ies'}${blocked} · click for path detail`;
  }
  if (edge.kind === 'flow_via_gateway') {
    return `${source} → ${target} · DNS resolved on EC2 gateway`;
  }
  if (edge.kind === 'to_port') {
    const portLabel = nodes.get(edge.target)?.label ?? edge.target;
    return `${source} → port ${portLabel} · gateway egress on this port`;
  }
  if (edge.kind === 'port_to_flow') {
    return `Port ${source} → ${target} · open connection`;
  }
  if (edge.kind === 'gateway_to_flow') {
    return `EC2 DNS → ${target} · open session`;
  }
  if (edge.kind === 'dns_to_flow') {
    return `${source} → ${target} · DNS name matched to open connection`;
  }
  if (edge.kind === 'flow_session') {
    return `${source} → ${target} · open connection (IP only, no DNS match yet)`;
  }
  if (edge.kind === 'dns_direct') {
    const blocked = edge.blocked_count > 0 ? ` · ${edge.blocked_count} blocked` : '';
    return `${source} → ${target} · ${edge.query_count} DNS (no app yet)${blocked}`;
  }
  const blocked = edge.blocked_count > 0 ? ` · ${edge.blocked_count} blocked` : '';
  return `${source} → ${target} · ${edge.query_count} DNS quer${edge.query_count === 1 ? 'y' : 'ies'}${blocked}`;
}

function isEdgeSimulatedCut(
  edge: NetworkMapEdge,
  whatIf: WhatIfSimulationResult | null,
  portWhatIf: PortWhatIfSimulationResult | null,
  tunnelWhatIf: TunnelWhatIfSimulationResult | null,
): boolean {
  if (tunnelWhatIf?.disabledEdgeKeys.has(edgeKey(edge))) {
    return true;
  }
  if (portWhatIf?.disabledEdgeKeys.has(edgeKey(edge))) {
    return true;
  }
  if (!whatIf) {
    return false;
  }
  if (edge.kind === 'path_egress') {
    return whatIf.disabledAppIds.has(edge.source);
  }
  if (edge.kind === 'path_forward') {
    return whatIf.simulatedBlockedDomainIds.has(edge.target);
  }
  return whatIf.disabledEdgeKeys.has(edgeKey(edge));
}

function edgeStroke(
  edge: NetworkMapEdge,
  theme: ReturnType<typeof useTheme>,
  simulatedCut: boolean,
): string {
  const muted = alpha(theme.palette.text.primary, theme.palette.mode === 'dark' ? 0.45 : 0.38);
  const strong = alpha(theme.palette.text.primary, theme.palette.mode === 'dark' ? 0.62 : 0.52);
  if (simulatedCut || edge.blocked_count > 0) {
    return theme.palette.error.main;
  }
  if (edge.kind === 'dns_direct' || edge.kind === 'flow_session') {
    return alpha(theme.palette.text.primary, 0.28);
  }
  if (
    edge.kind === 'path_tunnel' ||
    edge.kind === 'path_resolve' ||
    edge.kind === 'path_egress' ||
    edge.kind === 'to_port'
  ) {
    return strong;
  }
  return muted;
}

interface NetworkAttributionMapGraphProps {
  minutes?: number;
  showHeader?: boolean;
}

export default function NetworkAttributionMapGraph({
  minutes = DEFAULT_NETWORK_MAP_MINUTES,
  showHeader = true,
}: NetworkAttributionMapGraphProps) {
  const theme = useTheme();
  const { snapshot, attribution, loading, error, liveConnected } = useTwinGraph(
    minutes,
    undefined,
    true,
  );
  const [whatIfMode, setWhatIfMode] = useState(false);
  const [graphLayout, setGraphLayout] = useState<NetworkMapLayoutStyle>('columns');
  const [disabledAppIds, setDisabledAppIds] = useState<Set<string>>(new Set());
  const [disabledPortNumbers, setDisabledPortNumbers] = useState<Set<number>>(new Set());
  const [tunnelBlocked, setTunnelBlocked] = useState(false);
  const [gatewayBlocked, setGatewayBlocked] = useState(false);
  const [flowDestExpansion, setFlowDestExpansion] = useState<Record<string, PortDestExpansion>>({});
  const [selectedDomainId, setSelectedDomainId] = useState<string | null>(null);
  const [selectedClientId, setSelectedClientId] = useState<string | 'all'>('all');
  const [selectedRowId, setSelectedRowId] = useState<string | null>(null);
  const [sourceFilter, setSourceFilter] = useState<'all' | 'endpoint' | 'trusttwin'>('all');

  const layoutMode = 'unified' as const;

  const graphData = useMemo(() => {
    if (!snapshot) {
      return null;
    }
    return projectTwinGraph(snapshot, 'unified', attribution);
  }, [snapshot, attribution]);

  const allRows = useMemo(() => buildDestinationRows(graphData), [graphData]);

  const filteredRows = useMemo(() => {
    return allRows.filter((row) => {
      if (sourceFilter !== 'all' && row.source !== sourceFilter) {
        return false;
      }
      if (selectedClientId !== 'all' && row.clientId !== selectedClientId) {
        return false;
      }
      return true;
    });
  }, [allRows, sourceFilter, selectedClientId]);

  const clients = useMemo(() => listClientsFromRows(allRows), [allRows]);

  useEffect(() => {
    if (clients.length === 0) {
      return;
    }
    if (selectedClientId !== 'all' && !clients.some((c) => c.id === selectedClientId)) {
      setSelectedClientId(clients[0].id);
      return;
    }
    if (selectedClientId === 'all' && clients.length > 0) {
      setSelectedClientId(clients[0].id);
    }
  }, [clients, selectedClientId]);

  const selectedRow = useMemo(
    () => allRows.find((row) => row.id === selectedRowId) ?? null,
    [allRows, selectedRowId],
  );

  const displayGraph = useMemo(() => {
    if (!graphData) {
      return null;
    }
    const aggregated = aggregateFlowDestinations(
      graphData.nodes,
      graphData.edges,
      flowDestExpansion,
    );
    const clientScope = selectedClientId === 'all' ? clients[0]?.id ?? 'all' : selectedClientId;
    // Minimal path: spine only; expand one destination when a table row is selected.
    return focusPathGraph(aggregated, clientScope, selectedRow);
  }, [graphData, flowDestExpansion, selectedClientId, clients, selectedRow]);

  const data = attribution;

  const layout = useMemo(() => {
    if (!displayGraph) {
      return null;
    }
    if (graphLayout === 'force') {
      return layoutForceDirected(displayGraph.nodes, displayGraph.edges, layoutMode);
    }
    return layoutNetworkMap(displayGraph.nodes, displayGraph.edges, layoutMode);
  }, [displayGraph, graphLayout]);

  const nodeMap = useMemo(() => {
    const map = new Map<string, PositionedNode>();
    layout?.nodes.forEach((n) => map.set(n.id, n));
    return map;
  }, [layout]);

  const whatIf = useMemo(() => {
    if (!data || !whatIfMode) {
      return null;
    }
    return computeWhatIfSimulation(data.nodes, data.edges, disabledAppIds);
  }, [data, whatIfMode, disabledAppIds]);

  const portWhatIf = useMemo(() => {
    if (!graphData || !whatIfMode) {
      return null;
    }
    return computePortWhatIfSimulation(graphData.nodes, graphData.edges, disabledPortNumbers);
  }, [graphData, whatIfMode, disabledPortNumbers]);

  const tunnelWhatIf = useMemo(() => {
    if (!graphData || !whatIfMode) {
      return null;
    }
    return computeTunnelWhatIfSimulation(graphData.edges, tunnelBlocked, gatewayBlocked);
  }, [graphData, whatIfMode, tunnelBlocked, gatewayBlocked]);

  const activePortNumbers = useMemo(
    () => (graphData ? listActivePortNumbers(graphData.nodes) : []),
    [graphData],
  );

  const selectedFlows = useMemo((): PathFlowDetail[] => {
    if (!data || !selectedDomainId) {
      return [];
    }
    return buildPathFlowDetailsForDomain(selectedDomainId, data.nodes, data.edges);
  }, [data, selectedDomainId]);

  const appNodes = useMemo(
    () => (data?.nodes.filter((n) => n.type === 'app') ?? []) as NetworkMapNode[],
    [data],
  );

  const disabledAppLabels = useMemo(() => {
    if (!data || disabledAppIds.size === 0) {
      return [];
    }
    const byId = new Map(data.nodes.map((n) => [n.id, n.label]));
    return [...disabledAppIds].map((id) => byId.get(id) ?? id);
  }, [data, disabledAppIds]);

  const handleToggleApp = (appNodeId: string) => {
    setDisabledAppIds((prev) => toggleDisabledApp(prev, appNodeId));
  };

  const handleWhatIfModeChange = (enabled: boolean) => {
    setWhatIfMode(enabled);
    if (!enabled) {
      setDisabledAppIds(new Set());
      setDisabledPortNumbers(new Set());
      setTunnelBlocked(false);
      setGatewayBlocked(false);
    }
  };

  const handleTogglePort = (port: number) => {
    setDisabledPortNumbers((prev) => toggleDisabledPortNumber(prev, port));
  };

  const handleSimulationCommand = (response: SimulationCommandResponse) => {
    const enablesWhatIf =
      response.action === 'enable_what_if' ||
      response.action === 'block_port' ||
      response.action === 'unblock_port' ||
      response.action === 'block_gateway' ||
      response.action === 'unblock_gateway';
    if (enablesWhatIf) {
      setWhatIfMode(true);
    }
    if (response.action === 'clear_simulation') {
      setDisabledPortNumbers(new Set());
      setDisabledAppIds(new Set());
      setTunnelBlocked(false);
      setGatewayBlocked(false);
      return;
    }
    if (response.action === 'block_port' && response.port != null) {
      setDisabledPortNumbers((prev) => new Set(prev).add(response.port!));
    }
    if (response.action === 'unblock_port' && response.port != null) {
      setDisabledPortNumbers((prev) => {
        const next = new Set(prev);
        next.delete(response.port!);
        return next;
      });
    }
    if (response.action === 'block_gateway') {
      setGatewayBlocked(true);
    }
    if (response.action === 'unblock_gateway') {
      setGatewayBlocked(false);
    }
  };

  const handleExpandFlowAggregate = (node: NetworkMapNode) => {
    const hubKey = parseAggregateHubFromNode(node);
    if (hubKey == null) {
      return;
    }
    setFlowDestExpansion((prev) => {
      const current = prev[hubKey] ?? (node.type === 'flow_more' ? 'partial' : 'summary');
      return { ...prev, [hubKey]: nextPortDestExpansion(current) };
    });
  };

  const handleEdgeClick = (edge: NetworkMapEdge) => {
    if (!data) {
      return;
    }
    if (edge.kind === 'path_forward') {
      setSelectedDomainId(edge.target);
      return;
    }
    if (edge.kind === 'dns' || edge.kind === 'dns_direct') {
      setSelectedDomainId(edge.target);
    }
  };

  const handleDomainSelect = (domainId: string) => {
    setSelectedDomainId((prev) => (prev === domainId ? null : domainId));
  };

  const handleSelectRow = (row: DestinationRow) => {
    if (selectedRowId === row.id) {
      setSelectedRowId(null);
      setSelectedDomainId(null);
      return;
    }
    setSelectedRowId(row.id);
    setSelectedClientId(row.clientId);
    if (row.destinationKind === 'domain') {
      setSelectedDomainId(row.destinationId);
    } else {
      setSelectedDomainId(null);
    }
  };

  const pathClientLabel =
    clients.find((c) => c.id === selectedClientId)?.label ??
    (selectedClientId === 'all' ? 'All clients' : selectedClientId);

  const deviceCount = clients.length;
  const blockCount = filteredRows.filter((r) => r.action === 'block').length;
  const domainCount = filteredRows.filter((r) => r.destinationKind === 'domain').length;
  const flowCount = filteredRows.filter((r) => r.destinationKind === 'session').length;

  const summaryNodes = useMemo(() => {
    if (!layout) {
      return [];
    }
    const visible = layout.nodes.filter(
      (node) => node.type !== 'tunnel' && node.type !== 'gateway' && node.type !== 'policy',
    );
    const order: Record<string, number> = {
      flow: 0,
      flow_summary: 0,
      flow_more: 0,
      port: 1,
      domain: 2,
      app: 3,
      device: 4,
    };
    return [...visible].sort((a, b) => (order[a.type] ?? 9) - (order[b.type] ?? 9));
  }, [layout]);

  const landFill = theme.palette.mode === 'dark' ? '#0F1419' : '#F4F6F8';
  const gridDot = alpha(theme.palette.text.primary, theme.palette.mode === 'dark' ? 0.04 : 0.035);
  const laneStroke = alpha(theme.palette.divider, 0.35);
  const columnLabels = pathColumnLabels(layoutMode);
  const showColumnGuides = graphLayout === 'columns';

  return (
    <Paper variant="outlined" sx={{ p: 2, height: '100%' }}>
      {showHeader && (
        <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 1.5 }}>
          <HubIcon color="primary" fontSize="small" />
          <Typography variant="subtitle1" fontWeight={600} sx={{ flex: 1 }}>
            Network attribution map
          </Typography>
          {liveConnected && (
            <Chip size="small" label="Live DNS" color="success" variant="outlined" sx={{ height: 24 }} />
          )}
        </Stack>
      )}

      <Stack
        direction={{ xs: 'column', md: 'row' }}
        alignItems={{ xs: 'stretch', md: 'center' }}
        justifyContent="space-between"
        spacing={1}
        sx={{ mb: 1.5 }}
      >
        <Stack direction="row" flexWrap="wrap" gap={0.75} alignItems="center">
          <FormControl size="small" sx={{ minWidth: 180 }}>
            <InputLabel id="network-map-client-label">Client</InputLabel>
            <Select
              labelId="network-map-client-label"
              label="Client"
              value={clients.some((c) => c.id === selectedClientId) ? selectedClientId : ''}
              displayEmpty
              onChange={(e) => {
                setSelectedClientId(e.target.value as string);
                setSelectedRowId(null);
              }}
            >
              {clients.length === 0 && (
                <MenuItem value="" disabled>
                  No clients
                </MenuItem>
              )}
              {clients.map((client) => (
                <MenuItem key={client.id} value={client.id}>
                  {client.label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel id="network-map-source-label">Source</InputLabel>
            <Select
              labelId="network-map-source-label"
              label="Source"
              value={sourceFilter}
              onChange={(e) => setSourceFilter(e.target.value as 'all' | 'endpoint' | 'trusttwin')}
            >
              <MenuItem value="all">All</MenuItem>
              <MenuItem value="endpoint">Endpoint</MenuItem>
              <MenuItem value="trusttwin">Agents</MenuItem>
            </Select>
          </FormControl>
          <Chip size="small" variant="outlined" label={`${deviceCount} clients`} />
          <Chip size="small" variant="outlined" label={`${filteredRows.length} destinations`} />
          <Chip size="small" variant="outlined" label={`${domainCount} DNS`} />
          {blockCount > 0 && (
            <Chip size="small" color="error" variant="outlined" label={`${blockCount} blocked`} />
          )}
          {flowCount > 0 && (
            <Chip size="small" variant="outlined" label={`${flowCount} sessions`} />
          )}
          {data && <Chip size="small" variant="outlined" label={`Last ${data.minutes} min`} />}
        </Stack>
        <Stack direction="row" spacing={0.5} alignItems="center">
          <FormControlLabel
            control={
              <Switch
                size="small"
                checked={graphLayout === 'force'}
                onChange={(_, checked) => setGraphLayout(checked ? 'force' : 'columns')}
              />
            }
            label={
              <Stack direction="row" spacing={0.5} alignItems="center">
                <ScatterPlotIcon sx={{ fontSize: 16 }} />
                <Typography variant="body2">Organic layout</Typography>
              </Stack>
            }
            sx={{ m: 0 }}
          />
          <FormControlLabel
            control={
              <Switch
                size="small"
                checked={whatIfMode}
                onChange={(_, checked) => handleWhatIfModeChange(checked)}
              />
            }
            label={
              <Stack direction="row" spacing={0.5} alignItems="center">
                <ScienceIcon sx={{ fontSize: 16 }} />
                <Typography variant="body2">What-if</Typography>
              </Stack>
            }
            sx={{ m: 0 }}
          />
        </Stack>
      </Stack>

      <Typography variant="subtitle2" fontWeight={600} sx={{ mb: 0.75 }}>
        Destinations
      </Typography>
      <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 1 }}>
        Who talked to what. Click a row to inspect that destination on the path (click again to clear).
      </Typography>
      {loading && allRows.length === 0 ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
          <CircularProgress size={28} />
        </Box>
      ) : (
        <Box sx={{ mb: 2, border: `1px solid ${theme.palette.divider}`, borderRadius: 1 }}>
          <DestinationTable
            rows={filteredRows}
            selectedRowId={selectedRowId}
            onSelectRow={handleSelectRow}
          />
        </Box>
      )}

      <Typography variant="subtitle2" fontWeight={600} sx={{ mb: 0.75 }}>
        Path · {pathClientLabel}
        {selectedRow ? ` · ${selectedRow.destination}` : ''}
      </Typography>
      <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 1 }}>
        {selectedRow
          ? 'Path for the selected destination. Click another row or clear selection to return to the summary path.'
          : 'Summary path only (egress). Click a table row to inspect one destination.'}
      </Typography>

      <SimulationCommandBar
        activePorts={activePortNumbers}
        activeApps={appNodes.map((a) => a.label)}
        onCommand={handleSimulationCommand}
      />

      <Alert severity="info" sx={{ mb: 1.5 }} icon={<HubIcon fontSize="small" />}>
        Observability graph: device → process → EC2 Gateway → EC2 DNS → port → DNS name or session IP.
        Many sessions aggregate per port (click hub to expand). Policy gates are hidden.
      </Alert>

      {whatIfMode && (tunnelBlocked || gatewayBlocked) && (
        <Alert severity="warning" sx={{ mb: 1.5 }} icon={<ScienceIcon fontSize="small" />}>
          {tunnelBlocked && <>Simulating EC2 gateway down</>}
          {tunnelBlocked && gatewayBlocked && ' · '}
          {gatewayBlocked && <>Simulating EC2 DNS gateway failure</>}
          {' · '}
          {tunnelWhatIf?.affectedPathCount ?? 0} path edge
          {(tunnelWhatIf?.affectedPathCount ?? 0) === 1 ? '' : 's'} cut
          <Button
            size="small"
            sx={{ ml: 1, mt: { xs: 1, sm: 0 } }}
            onClick={() => {
              setTunnelBlocked(false);
              setGatewayBlocked(false);
            }}
          >
            Restore infra
          </Button>
        </Alert>
      )}

      {whatIfMode && disabledPortNumbers.size > 0 && (
        <Alert severity="info" sx={{ mb: 1.5 }} icon={<ScienceIcon fontSize="small" />}>
          Simulating blocked ports:{' '}
          <strong>{[...disabledPortNumbers].sort((a, b) => a - b).join(', ')}</strong>
          {' · '}
          EC2 would drop {portWhatIf?.affectedConnectionCount ?? 0} live session
          {(portWhatIf?.affectedConnectionCount ?? 0) === 1 ? '' : 's'}
          <Button
            size="small"
            sx={{ ml: 1, mt: { xs: 1, sm: 0 } }}
            onClick={() => setDisabledPortNumbers(new Set())}
          >
            Clear ports
          </Button>
        </Alert>
      )}

      {whatIfMode && (
        <Alert severity="info" sx={{ mb: 1.5 }} icon={<ScienceIcon fontSize="small" />}>
          {disabledAppIds.size === 0 ? (
            <>Select a process below or on the map to simulate it being disabled.</>
          ) : (
            <>
              Simulating disabled: <strong>{disabledAppLabels.join(', ')}</strong>
              {' · '}
              {whatIf?.affectedQueryCount ?? 0} DNS quer{(whatIf?.affectedQueryCount ?? 0) === 1 ? 'y' : 'ies'} cut
              {' · '}
              {whatIf?.affectedDomainCount ?? 0} destination{(whatIf?.affectedDomainCount ?? 0) === 1 ? '' : 's'} would lose access
            </>
          )}
          {disabledAppIds.size > 0 && (
            <Button size="small" sx={{ ml: 1, mt: { xs: 1, sm: 0 } }} onClick={() => setDisabledAppIds(new Set())}>
              Clear
            </Button>
          )}
        </Alert>
      )}

      {error && (
        <Alert severity="error" sx={{ mb: 1.5 }}>
          {error}
        </Alert>
      )}

      {whatIfMode && appNodes.length > 0 && (
        <Stack direction="row" flexWrap="wrap" gap={0.75} sx={{ mb: 1.5 }}>
          {appNodes.map((app) => {
            const selected = disabledAppIds.has(app.id);
            const icon = getNodeIconStyle({ type: 'app', app_slug: app.app_slug });
            return (
              <Chip
                key={app.id}
                size="small"
                variant={selected ? 'filled' : 'outlined'}
                color={selected ? 'error' : 'default'}
                icon={
                  selected ? (
                    <BlockIcon sx={{ fontSize: 14 }} />
                  ) : (
                    <Box component="span" sx={{ display: 'flex', color: icon.color, ml: 0.5 }}>
                      {icon.icon}
                    </Box>
                  )
                }
                label={`${selected ? 'Disable ' : ''}${app.label}`}
                onClick={() => handleToggleApp(app.id)}
                sx={{ cursor: 'pointer' }}
              />
            );
          })}
        </Stack>
      )}

      {whatIfMode && activePortNumbers.length > 0 && (
        <Stack direction="row" flexWrap="wrap" gap={0.75} sx={{ mb: 1.5 }}>
          {activePortNumbers.map((port) => {
            const selected = disabledPortNumbers.has(port);
            return (
              <Chip
                key={port}
                size="small"
                variant={selected ? 'filled' : 'outlined'}
                color={selected ? 'error' : 'default'}
                icon={selected ? <BlockIcon sx={{ fontSize: 14 }} /> : undefined}
                label={`${selected ? 'Block ' : ''}port ${port}`}
                onClick={() => handleTogglePort(port)}
                sx={{ cursor: 'pointer' }}
              />
            );
          })}
        </Stack>
      )}

      <Box
        sx={{
          position: 'relative',
          borderRadius: 1,
          overflow: 'auto',
          border: `1px solid ${whatIfMode ? theme.palette.warning.main : theme.palette.divider}`,
          bgcolor: landFill,
          minHeight: 300,
        }}
      >
        {loading && !layout && (
          <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 300 }}>
            <CircularProgress size={28} />
          </Box>
        )}

        {layout && layout.nodes.length > 0 && (
          <Box
            component="svg"
            viewBox={`0 0 ${layout.width} ${layout.height}`}
            preserveAspectRatio="xMidYMid meet"
            sx={{ width: '100%', minWidth: showColumnGuides ? 640 : undefined, height: 'auto', display: 'block', minHeight: 300 }}
            role="img"
            aria-label="Security observability graph with devices, DNS, endpoint agents, and live sessions"
          >
            <defs>
              <pattern id="network-map-grid" width="24" height="24" patternUnits="userSpaceOnUse">
                <path
                  d="M 24 0 L 0 0 0 24"
                  fill="none"
                  stroke={gridDot}
                  strokeWidth={1}
                />
              </pattern>
            </defs>
            <rect x={0} y={0} width={layout.width} height={layout.height} fill={landFill} />
            <rect x={0} y={0} width={layout.width} height={layout.height} fill="url(#network-map-grid)" />

            {showColumnGuides &&
              columnLabels.map(({ key, label }) => {
              const x = layout.columnGuides[key];
              if (x == null) {
                return null;
              }
              return (
                <g key={key}>
                  <line
                    x1={x}
                    y1={28}
                    x2={x}
                    y2={layout.height - 20}
                    stroke={laneStroke}
                    strokeDasharray="4 6"
                  />
                  <text x={x} y={18} textAnchor="middle" fontSize={9} fontWeight={600} fill={theme.palette.text.secondary}>
                    {label}
                  </text>
                </g>
              );
            })}

            {layout.edges.map((edge) => {
              const from = nodeMap.get(edge.source);
              const to = nodeMap.get(edge.target);
              if (!from || !to) {
                return null;
              }
              const simulatedCut = isEdgeSimulatedCut(edge, whatIf, portWhatIf, tunnelWhatIf);
              const stroke = edgeStroke(edge, theme, simulatedCut);
              const clickable =
                edge.kind === 'path_forward' || edge.kind === 'dns' || edge.kind === 'dns_direct';
              const strokeWidth =
                edge.kind === 'foreground' || edge.kind === 'path_tunnel' || edge.kind === 'path_resolve'
                  ? 1
                  : Math.min(1.75, 0.9 + Math.log2(edge.query_count + 1) * 0.28);
              const pathD = edgePath(from.x, from.y, to.x, to.y);
              return (
                <g key={`${edge.source}-${edge.target}-${edge.kind}`}>
                  <path
                    d={pathD}
                    fill="none"
                    stroke={stroke}
                    strokeWidth={strokeWidth}
                    strokeDasharray={
                      simulatedCut || edge.kind === 'dns_direct' || edge.kind === 'flow_session'
                        ? '4 3'
                        : undefined
                    }
                    opacity={simulatedCut ? 0.5 : 0.9}
                    strokeLinecap="square"
                    style={{ cursor: clickable ? 'pointer' : undefined }}
                    onClick={clickable ? () => handleEdgeClick(edge) : undefined}
                  >
                    <title>{edgeTooltip(edge, nodeMap, simulatedCut)}</title>
                  </path>
                </g>
              );
            })}

            {layout.nodes.map((node) => (
              <MapNodeGlyph
                key={node.id}
                node={node}
                whatIfMode={whatIfMode}
                portDisabled={
                  whatIfMode &&
                  ((node.type === 'port' &&
                    (() => {
                      const port = parsePortLabel(node.label);
                      return port != null && disabledPortNumbers.has(port);
                    })()) ||
                    ((node.type === 'flow_summary' || node.type === 'flow_more') &&
                      (() => {
                        const port = parseAggregatePortFromNode(node);
                        return port != null && disabledPortNumbers.has(port);
                      })()))
                }
                infraDisabled={
                  whatIfMode &&
                  ((node.type === 'tunnel' && tunnelBlocked) || (node.type === 'gateway' && gatewayBlocked))
                }
                appDisabled={whatIfMode && disabledAppIds.has(node.id)}
                simulatedBlocked={
                  (whatIf?.simulatedBlockedDomainIds.has(node.id) ?? false) ||
                  (portWhatIf?.simulatedBlockedFlowIds.has(node.id) ?? false)
                }
                selected={selectedDomainId === node.id}
                onSelectApp={handleToggleApp}
                onSelectDomain={handleDomainSelect}
                onSelectPort={handleTogglePort}
                onSelectTunnel={() => setTunnelBlocked((prev) => !prev)}
                onSelectGateway={() => setGatewayBlocked((prev) => !prev)}
                onExpandFlowAggregate={handleExpandFlowAggregate}
              />
            ))}
          </Box>
        )}

        {!loading && layout && layout.nodes.length === 0 && (
          <Box sx={{ p: 3 }}>
            <Typography variant="body2" color="text.secondary">
              No destinations in the last {data?.minutes ?? minutes} minutes. Endpoints appear after DNS
              queries or L4 flows; TrustTwin agents need shared Redis (<code>REDIS_URL</code>) and a
              network_summary with remote ports.
            </Typography>
          </Box>
        )}
      </Box>

      {selectedFlows.length > 0 && (
        <PathFlowDetailPanel flows={selectedFlows} onClose={() => setSelectedDomainId(null)} />
      )}

      {layout && layout.nodes.length > 0 && (
        <>
          <Stack direction="row" flexWrap="wrap" gap={0.75} sx={{ mt: 1.5 }}>
            <Chip size="small" variant="outlined" label="Teal = device" />
            <Chip size="small" variant="outlined" label="Center = process" />
            <Chip size="small" variant="outlined" label="Purple = EC2 Gateway" sx={{ borderColor: 'secondary.main', color: 'secondary.main' }} />
            <Chip size="small" variant="outlined" label="Blue = EC2 DNS" sx={{ borderColor: 'info.main', color: 'info.main' }} />
            <Chip size="small" variant="outlined" label="Purple = port hub" sx={{ borderColor: 'secondary.main', color: 'secondary.main' }} />
            <Chip size="small" variant="outlined" label="DNS name / session IP" />
            <Chip size="small" variant="outlined" label="Hub = aggregated sessions (click to expand)" />
            <Chip
              size="small"
              variant="outlined"
              label="Animated arc = live traffic"
              sx={{ borderColor: 'success.main', color: 'success.main' }}
            />
            <Chip
              size="small"
              variant="outlined"
              label="Dashed = no app yet"
              sx={{ borderColor: 'text.disabled', color: 'text.secondary' }}
            />
            {whatIfMode && (
              <Chip
                size="small"
                variant="outlined"
                label="Red cut = what-if disabled"
                sx={{ borderColor: 'error.main', color: 'error.main' }}
              />
            )}
          </Stack>

          <Box
            sx={{
              mt: 1.5,
              display: 'grid',
              gridTemplateColumns: { xs: '1fr', sm: 'repeat(3, 1fr)' },
              gap: 1,
            }}
          >
            {summaryNodes.slice(0, 12).map((node) => {
                const style = getNodeIconStyle({
                  type: node.type,
                  app_slug: node.app_slug,
                  blocked: node.blocked || (whatIf?.simulatedBlockedDomainIds.has(node.id) ?? false),
                  label: node.label,
                });
                const appDisabled = whatIfMode && disabledAppIds.has(node.id);
                const domainSelected = selectedDomainId === node.id;
                const simulatedBlocked = whatIf?.simulatedBlockedDomainIds.has(node.id) ?? false;
                return (
                  <Stack
                    key={node.id}
                    direction="row"
                    spacing={0.75}
                    alignItems="center"
                    onClick={
                      whatIfMode && node.type === 'app'
                        ? () => handleToggleApp(node.id)
                        : node.type === 'domain'
                          ? () => handleDomainSelect(node.id)
                          : undefined
                    }
                    sx={{
                      px: 1,
                      py: 0.5,
                      borderRadius: 1,
                      bgcolor: alpha(theme.palette.background.paper, 0.6),
                      border: `1px solid ${
                        appDisabled
                          ? theme.palette.error.main
                          : domainSelected
                            ? theme.palette.info.main
                            : simulatedBlocked
                              ? theme.palette.error.light
                              : theme.palette.divider
                      }`,
                      minWidth: 0,
                      opacity: appDisabled ? 0.55 : 1,
                      cursor:
                        (whatIfMode && node.type === 'app') || node.type === 'domain'
                          ? 'pointer'
                          : 'default',
                    }}
                  >
                    <Box
                      sx={{
                        width: 22,
                        height: 22,
                        borderRadius: '50%',
                        bgcolor: style.bg,
                        color: style.color,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        flexShrink: 0,
                        '& svg': { fontSize: 13 },
                      }}
                    >
                      {style.icon}
                    </Box>
                    <Typography variant="caption" noWrap title={node.label} sx={{ minWidth: 0 }}>
                      {node.type === 'flow' ? shortenLabel(node.label) : shortenLabel(node.label)}
                    </Typography>
                  </Stack>
                );
              })}
          </Box>
          {summaryNodes.length > 12 && (
            <Typography variant="caption" color="text.secondary" sx={{ mt: 0.75, display: 'block' }}>
              +{summaryNodes.length - 12} more — names under pins on the map
            </Typography>
          )}
        </>
      )}
    </Paper>
  );
}
