import { useMemo, useState } from 'react';
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
import { alpha, keyframes, useTheme } from '@mui/material/styles';
import HubIcon from '@mui/icons-material/Hub';
import ScienceIcon from '@mui/icons-material/Science';
import BlockIcon from '@mui/icons-material/Block';
import RouteIcon from '@mui/icons-material/Route';
import SettingsEthernetIcon from '@mui/icons-material/SettingsEthernet';
import ScatterPlotIcon from '@mui/icons-material/ScatterPlot';
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
import { flowNodeTooltip, parseFlowNode, portNodeTooltip } from '../utils/flowLabels';
import {
  computePortWhatIfSimulation,
  listActivePortNumbers,
  PortWhatIfSimulationResult,
  toggleDisabledPortNumber,
} from '../utils/portWhatIfSimulation';
import {
  aggregateFlowDestinations,
  nextPortDestExpansion,
  parseAggregatePortFromNode,
  PortDestExpansion,
} from '../utils/aggregateFlowDestinations';
import { getNodeIconStyle } from '../utils/appIcons';
import {
  estimateBadgeWidth,
  formatPinLabel,
  getNodeVisualSpec,
  GRAPH_BADGE,
  semanticLaneXs,
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

const flowPulse = keyframes`
  to {
    stroke-dashoffset: -18;
  }
`;

interface MapNodeGlyphProps {
  node: PositionedNode;
  whatIfMode: boolean;
  pathViewMode: boolean;
  flowViewMode: boolean;
  portDisabled: boolean;
  appDisabled: boolean;
  simulatedBlocked: boolean;
  selected: boolean;
  onSelectApp?: (nodeId: string) => void;
  onSelectDomain?: (nodeId: string) => void;
  onSelectPort?: (port: number) => void;
  onExpandFlowAggregate?: (node: NetworkMapNode) => void;
}

function MapNodeGlyph({
  node,
  whatIfMode,
  pathViewMode,
  flowViewMode,
  portDisabled,
  appDisabled,
  simulatedBlocked,
  selected,
  onSelectApp,
  onSelectDomain,
  onSelectPort,
  onExpandFlowAggregate,
}: MapNodeGlyphProps) {
  const theme = useTheme();
  const style = getNodeIconStyle({
    type: node.type,
    app_slug: node.app_slug,
    blocked: node.blocked || simulatedBlocked,
  });
  const visual = getNodeVisualSpec(node.type);
  const nodeR = visual.radius;
  const iconSize = visual.iconSize;

  const isInfra = node.type === 'tunnel' || node.type === 'gateway' || node.type === 'policy';

  const ring = appDisabled || portDisabled
    ? theme.palette.error.main
    : selected
      ? theme.palette.info.main
      : node.type === 'device' && node.fresh
        ? theme.palette.success.main
        : node.type === 'domain' && (node.blocked || simulatedBlocked)
          ? theme.palette.error.main
          : isInfra
            ? style.color
            : alpha(style.color, 0.85);

  const tooltipParts = [
    node.type === 'app'
      ? `${node.label} (foreground process)`
      : node.type === 'domain'
        ? `${node.label}${node.blocked ? ' · blocked' : ''}${simulatedBlocked ? ' · would lose access (what-if)' : ''}`
        : node.type === 'flow'
          ? (() => {
              const parsed = parseFlowNode(node);
              return parsed
                ? `Open ${parsed.protocol.toUpperCase()} connection to ${node.label} on port ${parsed.port}`
                : flowNodeTooltip(node.label);
            })()
          : node.type === 'flow_summary'
            ? `${node.label} · click to expand top destinations`
            : node.type === 'flow_more'
              ? `${node.label} · click to show all destinations`
          : node.type === 'port'
            ? portNodeTooltip(Number(node.label))
          : node.type === 'gateway'
            ? `${node.label} · dnsmasq resolver on EC2`
          : node.type === 'tunnel'
            ? `${node.label} · VPN tunnel to gateway`
          : node.type === 'policy'
              ? `${node.label} · allow / block decision`
              : `${node.label}${node.client_ip ? ` · ${node.client_ip}` : ''}`,
  ];
  if (whatIfMode && node.type === 'app') {
    tooltipParts.push(appDisabled ? 'Click to re-enable in what-if' : 'Click to disable in what-if');
  }
  if (whatIfMode && node.type === 'port' && flowViewMode) {
    tooltipParts.push(portDisabled ? 'Click to unblock in what-if' : 'Click to simulate blocking this port');
  }
  if (pathViewMode && node.type === 'domain') {
    tooltipParts.push('Click to inspect DNS path');
  }

  const selectableApp = whatIfMode && node.type === 'app' && !flowViewMode;
  const selectablePort = whatIfMode && flowViewMode && node.type === 'port';
  const selectableDomain = pathViewMode && node.type === 'domain';
  const expandableAggregate =
    flowViewMode && (node.type === 'flow_summary' || node.type === 'flow_more');
  const pinLabel = formatPinLabel(node, flowViewMode);
  const showBadge = visual.showBadge && pinLabel != null;
  const badgeWidth = showBadge ? estimateBadgeWidth(pinLabel!, visual.badgeMonospace) : 0;
  const badgeY = nodeR + GRAPH_BADGE.offsetY;

  return (
    <g
      transform={`translate(${node.x}, ${node.y})`}
      style={{
        cursor: selectableApp || selectableDomain || selectablePort || expandableAggregate ? 'pointer' : 'default',
        opacity: appDisabled || portDisabled ? 0.45 : 1,
      }}
      filter="url(#network-map-node-shadow)"
      onClick={
        selectableApp
          ? () => onSelectApp?.(node.id)
          : selectableDomain
            ? () => onSelectDomain?.(node.id)
            : selectablePort
              ? () => onSelectPort?.(Number(node.label))
              : expandableAggregate
                ? () => onExpandFlowAggregate?.(node)
                : undefined
      }
    >
      <title>{tooltipParts.join(' · ')}</title>
      <circle
        r={nodeR + 4}
        fill={theme.palette.background.paper}
        stroke={ring}
        strokeWidth={
          selected ? 2 : appDisabled || portDisabled ? 2 : node.type === 'device' && node.fresh ? 1.75 : 1.5
        }
        strokeDasharray={appDisabled || portDisabled ? '4 3' : undefined}
      />
      <circle r={nodeR} fill={style.bg} stroke={alpha(style.color, 0.35)} strokeWidth={1} />
      {isInfra && (
        <circle
          r={nodeR - 3}
          fill="none"
          stroke={alpha(style.color, 0.2)}
          strokeWidth={1}
        />
      )}
      {appDisabled && (
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
            fill={alpha(theme.palette.background.paper, 0.92)}
            stroke={alpha(ring, 0.55)}
            strokeWidth={1}
          />
          <text
            y={badgeY + GRAPH_BADGE.height / 2 + 3.5}
            textAnchor="middle"
            fontSize={GRAPH_BADGE.fontSize}
            fontWeight={GRAPH_BADGE.fontWeight}
            fill={theme.palette.text.primary}
            style={{ fontFamily: visual.badgeMonospace ? 'ui-monospace, monospace' : undefined }}
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
    return `${source} → ${target} · DNS leaves endpoint via VPN (${edge.query_count} quer${edge.query_count === 1 ? 'y' : 'ies'})`;
  }
  if (edge.kind === 'path_tunnel') {
    return `${source} → ${target} · encrypted tunnel transit`;
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
  pathViewMode: boolean,
  flowViewMode: boolean,
): boolean {
  if (portWhatIf && flowViewMode) {
    return portWhatIf.disabledEdgeKeys.has(edgeKey(edge));
  }
  if (!whatIf) {
    return false;
  }
  if (pathViewMode) {
    if (edge.kind === 'path_egress') {
      return whatIf.disabledAppIds.has(edge.source);
    }
    if (edge.kind === 'path_forward') {
      return whatIf.simulatedBlockedDomainIds.has(edge.target);
    }
    return false;
  }
  return whatIf.disabledEdgeKeys.has(edgeKey(edge));
}

function edgeStroke(
  edge: NetworkMapEdge,
  theme: ReturnType<typeof useTheme>,
  simulatedCut: boolean,
): string {
  if (simulatedCut) {
    return theme.palette.error.main;
  }
  if (edge.kind === 'foreground') {
    return theme.palette.info.main;
  }
  if (edge.kind === 'path_tunnel' || edge.kind === 'path_resolve') {
    return theme.palette.secondary.main;
  }
  if (edge.kind === 'path_egress') {
    return theme.palette.primary.main;
  }
  if (edge.kind === 'path_forward') {
    return edge.blocked_count > 0 ? theme.palette.error.main : theme.palette.success.main;
  }
  if (edge.kind === 'flow_via_gateway') {
    return theme.palette.info.main;
  }
  if (edge.kind === 'to_port') {
    return alpha(theme.palette.secondary.main, 0.72);
  }
  if (edge.kind === 'port_to_flow') {
    return alpha(theme.palette.info.main, 0.78);
  }
  if (edge.kind === 'dns_to_flow') {
    return alpha(theme.palette.info.main, 0.65);
  }
  if (edge.kind === 'flow_session') {
    return alpha(theme.palette.info.main, 0.55);
  }
  if (edge.kind === 'dns_direct') {
    return theme.palette.text.disabled;
  }
  return edge.blocked_count > 0 ? theme.palette.error.main : theme.palette.success.main;
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
  const [flowViewMode, setFlowViewMode] = useState(false);
  const { snapshot, attribution, loading, error, liveConnected } = useTwinGraph(
    minutes,
    undefined,
    flowViewMode,
  );
  const [whatIfMode, setWhatIfMode] = useState(false);
  const [pathViewMode, setPathViewMode] = useState(false);
  const [graphLayout, setGraphLayout] = useState<NetworkMapLayoutStyle>('columns');
  const [disabledAppIds, setDisabledAppIds] = useState<Set<string>>(new Set());
  const [disabledPortNumbers, setDisabledPortNumbers] = useState<Set<number>>(new Set());
  const [portDestExpansion, setPortDestExpansion] = useState<Record<number, PortDestExpansion>>({});
  const [selectedDomainId, setSelectedDomainId] = useState<string | null>(null);

  const layoutMode = pathViewMode ? 'path' : flowViewMode ? 'flow' : 'attribution';

  const graphData = useMemo(() => {
    if (!snapshot) {
      return null;
    }
    const mode = pathViewMode ? 'path' : flowViewMode ? 'flow' : 'attribution';
    return projectTwinGraph(snapshot, mode, attribution);
  }, [snapshot, attribution, pathViewMode, flowViewMode]);

  const displayGraph = useMemo(() => {
    if (!graphData || !flowViewMode) {
      return graphData;
    }
    return aggregateFlowDestinations(graphData.nodes, graphData.edges, portDestExpansion);
  }, [graphData, flowViewMode, portDestExpansion]);

  const data = attribution;

  const layout = useMemo(() => {
    if (!displayGraph) {
      return null;
    }
    if (graphLayout === 'force') {
      return layoutForceDirected(displayGraph.nodes, displayGraph.edges, layoutMode);
    }
    return layoutNetworkMap(displayGraph.nodes, displayGraph.edges, layoutMode);
  }, [displayGraph, layoutMode, graphLayout]);

  const nodeMap = useMemo(() => {
    const map = new Map<string, PositionedNode>();
    layout?.nodes.forEach((n) => map.set(n.id, n));
    return map;
  }, [layout]);

  const whatIf = useMemo(() => {
    if (!data || !whatIfMode || flowViewMode) {
      return null;
    }
    return computeWhatIfSimulation(data.nodes, data.edges, disabledAppIds);
  }, [data, whatIfMode, disabledAppIds, flowViewMode]);

  const portWhatIf = useMemo(() => {
    if (!graphData || !whatIfMode || !flowViewMode) {
      return null;
    }
    return computePortWhatIfSimulation(graphData.nodes, graphData.edges, disabledPortNumbers);
  }, [graphData, whatIfMode, flowViewMode, disabledPortNumbers]);

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
    }
  };

  const handlePathViewChange = (enabled: boolean) => {
    setPathViewMode(enabled);
    if (enabled) {
      setFlowViewMode(false);
    }
    if (!enabled) {
      setSelectedDomainId(null);
    }
  };

  const handleFlowViewChange = (enabled: boolean) => {
    setFlowViewMode(enabled);
    if (enabled) {
      setPathViewMode(false);
    }
    if (!enabled) {
      setDisabledPortNumbers(new Set());
      setPortDestExpansion({});
    }
  };

  const handleTogglePort = (port: number) => {
    setDisabledPortNumbers((prev) => toggleDisabledPortNumber(prev, port));
  };

  const handleExpandFlowAggregate = (node: NetworkMapNode) => {
    const port = parseAggregatePortFromNode(node);
    if (port == null) {
      return;
    }
    setPortDestExpansion((prev) => {
      const current = prev[port] ?? (node.type === 'flow_more' ? 'partial' : 'summary');
      return { ...prev, [port]: nextPortDestExpansion(current) };
    });
  };

  const handleSimulationCommand = (response: SimulationCommandResponse) => {
    if (response.action === 'enable_what_if' || response.action === 'block_port' || response.action === 'unblock_port') {
      setWhatIfMode(true);
      if (!flowViewMode) {
        setFlowViewMode(true);
        setPathViewMode(false);
      }
    }
    if (response.action === 'clear_simulation') {
      setDisabledPortNumbers(new Set());
      setDisabledAppIds(new Set());
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
  };

  const handleEdgeClick = (edge: NetworkMapEdge) => {
    if (!pathViewMode || !data) {
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

  const deviceCount = data?.nodes.filter((n) => n.type === 'device').length ?? 0;
  const appCount = data?.nodes.filter((n) => n.type === 'app').length ?? 0;
  const domainCount = data?.nodes.filter((n) => n.type === 'domain').length ?? 0;
  const flowCount = graphData?.nodes.filter((n) => n.type === 'flow').length ?? 0;

  const summaryNodes = useMemo(() => {
    if (!layout) {
      return [];
    }
    const visible = layout.nodes.filter(
      (node) => node.type !== 'tunnel' && node.type !== 'gateway' && node.type !== 'policy',
    );
    if (!flowViewMode) {
      return visible;
    }
    const order: Record<string, number> = {
      flow: 0,
      flow_summary: 0,
      flow_more: 0,
      port: 1,
      gateway: 2,
      app: 3,
      device: 4,
    };
    return [...visible].sort((a, b) => (order[a.type] ?? 9) - (order[b.type] ?? 9));
  }, [layout, flowViewMode]);

  const landFill = theme.palette.mode === 'dark' ? '#0B1220' : '#F8FAFC';
  const gridDot = alpha(theme.palette.text.primary, theme.palette.mode === 'dark' ? 0.08 : 0.06);
  const laneStroke = alpha(theme.palette.divider, 0.45);
  const columnLabels = pathColumnLabels(layoutMode);
  const showColumnGuides = graphLayout === 'columns';
  const showForceSwimlanes = graphLayout === 'force' && (flowViewMode || pathViewMode);

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
        direction={{ xs: 'column', sm: 'row' }}
        alignItems={{ xs: 'flex-start', sm: 'center' }}
        justifyContent="space-between"
        spacing={1}
        sx={{ mb: 1.5 }}
      >
        <Stack direction="row" flexWrap="wrap" gap={0.75}>
          <Chip size="small" variant="outlined" label={`${deviceCount} devices`} />
          <Chip size="small" variant="outlined" label={`${appCount} apps`} />
          <Chip size="small" variant="outlined" label={`${domainCount} destinations`} />
          {data && <Chip size="small" variant="outlined" label={`Last ${data.minutes} min`} />}
          {flowViewMode && flowCount > 0 && (
            <Chip size="small" variant="outlined" label={`${flowCount} live connections`} />
          )}
        </Stack>
        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={0.5} alignItems={{ xs: 'flex-start', sm: 'center' }}>
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
                <Typography variant="body2">Graph layout</Typography>
              </Stack>
            }
            sx={{ m: 0 }}
          />
          <FormControlLabel
            control={
              <Switch
                size="small"
                checked={flowViewMode}
                onChange={(_, checked) => handleFlowViewChange(checked)}
              />
            }
            label={
              <Stack direction="row" spacing={0.5} alignItems="center">
                <SettingsEthernetIcon sx={{ fontSize: 16 }} />
                <Typography variant="body2">Flow view</Typography>
              </Stack>
            }
            sx={{ m: 0 }}
          />
          <FormControlLabel
            control={
              <Switch
                size="small"
                checked={pathViewMode}
                onChange={(_, checked) => handlePathViewChange(checked)}
              />
            }
            label={
              <Stack direction="row" spacing={0.5} alignItems="center">
                <RouteIcon sx={{ fontSize: 16 }} />
                <Typography variant="body2">Path view</Typography>
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

      {graphLayout === 'force' && (
        <Alert severity="info" sx={{ mb: 1.5 }} icon={<ScatterPlotIcon fontSize="small" />}>
          Graph layout places nodes by connectivity (spring force). Turn off to return to column view.
        </Alert>
      )}

      {flowViewMode && (
        <Alert severity="info" sx={{ mb: 1.5 }} icon={<SettingsEthernetIcon fontSize="small" />}>
          <strong>EC2 DNS</strong> is your gateway resolver (dnsmasq). All resolved traffic flows{' '}
          EC2 → port hub → destination. Destinations are aggregated per port (click to expand). Turn on{' '}
          <strong>What-if</strong> to simulate blocking a port at the gateway.
        </Alert>
      )}

      {flowViewMode && (
        <SimulationCommandBar
          activePorts={activePortNumbers}
          activeApps={appNodes.map((a) => a.label)}
          onCommand={handleSimulationCommand}
        />
      )}

      {pathViewMode && (
        <Alert severity="info" sx={{ mb: 1.5 }} icon={<RouteIcon fontSize="small" />}>
          Path view shows the logical DNS journey: endpoint → WireGuard → TrustEdge DNS → policy → destination.
          Click a destination or green/red path arc for step-by-step detail.
        </Alert>
      )}

      {whatIfMode && flowViewMode && (
        <Alert severity="info" sx={{ mb: 1.5 }} icon={<ScienceIcon fontSize="small" />}>
          {disabledPortNumbers.size === 0 ? (
            <>Click a port chip below or purple port pin on the map to simulate blocking that port.</>
          ) : (
            <>
              Simulating blocked ports:{' '}
              <strong>{[...disabledPortNumbers].sort((a, b) => a - b).join(', ')}</strong>
              {' · '}
              EC2 would drop {portWhatIf?.affectedConnectionCount ?? 0} live connection
              {(portWhatIf?.affectedConnectionCount ?? 0) === 1 ? '' : 's'} on{' '}
              {disabledPortNumbers.size === 1 ? 'this port' : 'these ports'}
            </>
          )}
          {disabledPortNumbers.size > 0 && (
            <Button
              size="small"
              sx={{ ml: 1, mt: { xs: 1, sm: 0 } }}
              onClick={() => setDisabledPortNumbers(new Set())}
            >
              Clear
            </Button>
          )}
        </Alert>
      )}

      {whatIfMode && !flowViewMode && (
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

      {whatIfMode && !flowViewMode && appNodes.length > 0 && (
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

      {whatIfMode && flowViewMode && activePortNumbers.length > 0 && (
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
          border: `1px solid ${
            whatIfMode
              ? theme.palette.info.main
              : pathViewMode
                ? theme.palette.secondary.main
                : flowViewMode
                  ? theme.palette.info.dark
                  : theme.palette.divider
          }`,
          bgcolor: landFill,
          minHeight: 300,
          boxShadow: theme.palette.mode === 'dark' ? 'inset 0 1px 0 rgba(255,255,255,0.04)' : 'inset 0 1px 0 rgba(0,0,0,0.03)',
          '& .network-flow-active': {
            strokeDasharray: '6 6',
            animation: `${flowPulse} 2s linear infinite`,
          },
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
            sx={{ width: '100%', minWidth: showColumnGuides && (flowViewMode || pathViewMode) ? 640 : undefined, height: 'auto', display: 'block', minHeight: 300 }}
            role="img"
            aria-label={
              graphLayout === 'force'
                ? 'Force-directed network graph'
                : flowViewMode
                ? 'Network map with DNS names and live TCP/UDP connections'
                : pathViewMode
                  ? 'Network map with DNS path through WireGuard, gateway, and policy'
                  : 'Network map with devices, processes, and DNS destinations connected by arcs'
            }
          >
            <defs>
              <pattern id="network-map-grid" width="20" height="20" patternUnits="userSpaceOnUse">
                <circle cx="1" cy="1" r="0.75" fill={gridDot} />
              </pattern>
              <filter id="network-map-node-shadow" x="-50%" y="-50%" width="200%" height="200%">
                <feDropShadow dx="0" dy="1" stdDeviation="1.8" floodColor="#000" floodOpacity={theme.palette.mode === 'dark' ? 0.35 : 0.12} />
              </filter>
            </defs>
            <rect x={0} y={0} width={layout.width} height={layout.height} fill="url(#network-map-grid)" />

            {showForceSwimlanes &&
              semanticLaneXs(layoutMode, layout.width).map((x, index) => {
                const label = columnLabels[index]?.label;
                if (!label) {
                  return null;
                }
                return (
                  <g key={`lane-${columnLabels[index]?.key ?? index}`}>
                    <line
                      x1={x}
                      y1={24}
                      x2={x}
                      y2={layout.height - 16}
                      stroke={laneStroke}
                      strokeDasharray="3 8"
                      strokeWidth={1}
                    />
                    <text
                      x={x}
                      y={14}
                      textAnchor="middle"
                      fontSize={8.5}
                      fontWeight={600}
                      letterSpacing={0.4}
                      fill={alpha(theme.palette.text.secondary, 0.75)}
                    >
                      {label.toUpperCase()}
                    </text>
                  </g>
                );
              })}

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
              const simulatedCut = isEdgeSimulatedCut(edge, whatIf, portWhatIf, pathViewMode, flowViewMode);
              const animated =
                !simulatedCut &&
                (edge.kind === 'dns' ||
                  edge.kind === 'dns_direct' ||
                  edge.kind === 'path_forward' ||
                  edge.kind === 'path_egress' ||
                  edge.kind === 'port_to_flow');
              const stroke = edgeStroke(edge, theme, simulatedCut);
              const clickable =
                pathViewMode && (edge.kind === 'path_forward' || edge.kind === 'dns' || edge.kind === 'dns_direct');
              const strokeWidth =
                edge.kind === 'foreground' || edge.kind === 'path_tunnel' || edge.kind === 'path_resolve'
                  ? 1.25
                  : Math.min(2.5, 1 + Math.log2(edge.query_count + 1) * 0.45);
              const pathD = edgePath(from.x, from.y, to.x, to.y);
              return (
                <g key={`${edge.source}-${edge.target}-${edge.kind}`}>
                  <path
                    d={pathD}
                    fill="none"
                    stroke={alpha(stroke, 0.18)}
                    strokeWidth={strokeWidth + 2.5}
                    strokeLinecap="round"
                    style={{ pointerEvents: 'none' }}
                  />
                  <path
                    d={pathD}
                    fill="none"
                    stroke={stroke}
                    strokeWidth={strokeWidth}
                  strokeDasharray={
                    simulatedCut ||
                    edge.kind === 'dns_direct' ||
                    edge.kind === 'flow_session' ||
                    edge.kind === 'path_tunnel'
                      ? '5 4'
                      : undefined
                  }
                  opacity={
                    simulatedCut
                      ? 0.55
                      : edge.kind === 'foreground'
                        ? 0.5
                        : edge.kind === 'dns_direct'
                          ? 0.45
                          : edge.kind === 'path_tunnel' || edge.kind === 'path_resolve'
                            ? 0.65
                            : 0.8
                  }
                  strokeLinecap="round"
                  className={animated ? 'network-flow-active' : undefined}
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
                pathViewMode={pathViewMode}
                flowViewMode={flowViewMode}
                appDisabled={whatIfMode && !flowViewMode && disabledAppIds.has(node.id)}
                portDisabled={
                  whatIfMode &&
                  flowViewMode &&
                  ((node.type === 'port' && disabledPortNumbers.has(Number(node.label))) ||
                    ((node.type === 'flow_summary' || node.type === 'flow_more') &&
                      (() => {
                        const port = parseAggregatePortFromNode(node);
                        return port != null && disabledPortNumbers.has(port);
                      })()))
                }
                simulatedBlocked={
                  (whatIf?.simulatedBlockedDomainIds.has(node.id) ?? false) ||
                  (portWhatIf?.simulatedBlockedFlowIds.has(node.id) ?? false)
                }
                selected={selectedDomainId === node.id}
                onSelectApp={handleToggleApp}
                onSelectDomain={handleDomainSelect}
                onSelectPort={handleTogglePort}
                onExpandFlowAggregate={handleExpandFlowAggregate}
              />
            ))}
          </Box>
        )}

        {!loading && layout && layout.nodes.length === 0 && (
          <Box sx={{ p: 3 }}>
            <Typography variant="body2" color="text.secondary">
              No network activity in the last {data?.minutes ?? minutes} minutes. Connect a client and browse
              to populate the map.
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
            <Chip size="small" variant="outlined" label="Teal pin = device" />
            <Chip size="small" variant="outlined" label="Center = process" />
            {flowViewMode ? (
              <>
                <Chip size="small" variant="outlined" label="Blue = EC2 DNS gateway" sx={{ borderColor: 'info.main', color: 'info.main' }} />
                <Chip size="small" variant="outlined" label="Purple pin = port hub" sx={{ borderColor: 'secondary.main', color: 'secondary.main' }} />
                <Chip size="small" variant="outlined" label="Cyan = destination IP (aggregated)" sx={{ borderColor: 'info.dark', color: 'info.dark' }} />
                <Chip size="small" variant="outlined" label="Hub icon = N on port (click to expand)" />
              </>
            ) : pathViewMode ? (
              <>
                <Chip size="small" variant="outlined" label="Purple = WireGuard" />
                <Chip size="small" variant="outlined" label="Blue = TrustEdge DNS" />
                <Chip size="small" variant="outlined" label="Amber = policy gate" />
              </>
            ) : (
              <Chip size="small" variant="outlined" label="Right = DNS destination" />
            )}
            <Chip
              size="small"
              variant="outlined"
              label="Animated arc = live DNS"
              sx={{ borderColor: 'success.main', color: 'success.main' }}
            />
            {!pathViewMode && !flowViewMode && (
              <Chip
                size="small"
                variant="outlined"
                label="Dashed = no app yet"
                sx={{ borderColor: 'text.disabled', color: 'text.secondary' }}
              />
            )}
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
                });
                const appDisabled = whatIfMode && !flowViewMode && disabledAppIds.has(node.id);
                const portDisabled =
                  whatIfMode && flowViewMode && node.type === 'port' && disabledPortNumbers.has(Number(node.label));
                const domainSelected = pathViewMode && selectedDomainId === node.id;
                const simulatedBlocked =
                  (whatIf?.simulatedBlockedDomainIds.has(node.id) ?? false) ||
                  (portWhatIf?.simulatedBlockedFlowIds.has(node.id) ?? false);
                return (
                  <Stack
                    key={node.id}
                    direction="row"
                    spacing={0.75}
                    alignItems="center"
                    onClick={
                      whatIfMode && !flowViewMode && node.type === 'app'
                        ? () => handleToggleApp(node.id)
                        : whatIfMode && flowViewMode && node.type === 'port'
                          ? () => handleTogglePort(Number(node.label))
                          : pathViewMode && node.type === 'domain'
                            ? () => handleDomainSelect(node.id)
                            : undefined
                    }
                    sx={{
                      px: 1,
                      py: 0.5,
                      borderRadius: 1,
                      bgcolor: alpha(theme.palette.background.paper, 0.6),
                      border: `1px solid ${
                        appDisabled || portDisabled
                          ? theme.palette.error.main
                          : domainSelected
                            ? theme.palette.info.main
                            : simulatedBlocked
                              ? theme.palette.error.light
                              : theme.palette.divider
                      }`,
                      minWidth: 0,
                      opacity: appDisabled || portDisabled ? 0.55 : 1,
                      cursor:
                        (whatIfMode && !flowViewMode && node.type === 'app') ||
                        (whatIfMode && flowViewMode && node.type === 'port') ||
                        (pathViewMode && node.type === 'domain')
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
                      {node.type === 'port'
                        ? `port ${node.label}`
                        : node.type === 'flow'
                          ? shortenLabel(node.label)
                          : shortenLabel(node.label)}
                    </Typography>
                  </Stack>
                );
              })}
          </Box>
          {summaryNodes.length > 12 && (
            <Typography variant="caption" color="text.secondary" sx={{ mt: 0.75, display: 'block' }}>
              +{summaryNodes.length - 12} more
              {flowViewMode ? ' connections' : ''} — names under pins on the map
            </Typography>
          )}
        </>
      )}
    </Paper>
  );
}
