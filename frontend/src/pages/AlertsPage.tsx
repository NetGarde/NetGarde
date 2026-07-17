import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Chip from '@mui/material/Chip';
import Stack from '@mui/material/Stack';
import Paper from '@mui/material/Paper';
import List from '@mui/material/List';
import ListItemButton from '@mui/material/ListItemButton';
import ListItemText from '@mui/material/ListItemText';
import Divider from '@mui/material/Divider';
import IconButton from '@mui/material/IconButton';
import Tooltip from '@mui/material/Tooltip';
import CircularProgress from '@mui/material/CircularProgress';
import ToggleButton from '@mui/material/ToggleButton';
import ToggleButtonGroup from '@mui/material/ToggleButtonGroup';
import Collapse from '@mui/material/Collapse';
import Button from '@mui/material/Button';
import Alert from '@mui/material/Alert';
import RefreshIcon from '@mui/icons-material/Refresh';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import ArrowForwardIcon from '@mui/icons-material/ArrowForward';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import { useMemo, useState, type MouseEvent } from 'react';
import { twinApi } from '../features/twin/config/api';
import { useSecurityAlerts } from '../features/twin/hooks/useSecurityAlerts';
import { SecurityAlert } from '../features/twin/types/securityAlert';
import { formatShortDateTime } from '../shared/utils/dateUtils';

const SEVERITY_COLOR: Record<string, 'error' | 'warning' | 'info' | 'default'> = {
  high: 'error',
  medium: 'warning',
  low: 'info',
};

const TYPE_LABEL: Record<string, string> = {
  temp_path_execution: 'Temp path execution',
  shell_spawns_downloader: 'Shell spawned downloader',
  script_spawns_shell: 'Script spawned shell',
  process_burst: 'Process burst',
  binary_path_mismatch: 'Binary path mismatch',
  new_public_ip: 'New public IP',
  network_type_change: 'Network type change',
  network_change_while_active: 'Network change while active',
  simultaneous_ip_and_type_change: 'IP and type change',
  rapid_public_ip_changes: 'Rapid public IP changes',
  double_ip_change_10m: 'Double IP change',
  network_type_flapping: 'Network type flapping',
  network_flap_5m: 'Network flap',
  event_burst: 'Event burst',
  active_ip_churn: 'Active IP churn',
  driver_load: 'Driver loaded',
  service_install: 'Service installed',
  registry_persistence: 'Persistence artifact',
};

const DETAIL_LABELS: Record<string, string> = {
  parent_comm: 'Parent',
  child_comm: 'Child',
  parent_pid: 'Parent PID',
  child_pid: 'Child PID',
  parent_cmdline: 'Parent command',
  child_cmdline: 'Child command',
  cmdline: 'Command',
  executable: 'Executable',
  comm: 'Process',
  pid: 'PID',
  from: 'From',
  to: 'To',
  from_ip: 'From IP',
  to_ip: 'To IP',
  from_type: 'From type',
  to_type: 'To type',
  ips: 'IPs',
  changes: 'Changes',
  count: 'Count',
  window_minutes: 'Window (min)',
  presence: 'Presence',
  listening_count: 'Listening ports',
  network_events: 'Network events',
  sample_limit: 'Sample size',
  top_comms: 'Top processes',
  processes: 'Recent processes',
  name: 'Name',
  display_name: 'Display name',
  state: 'State',
  status: 'Status',
  path: 'Path',
  service_type: 'Service type',
  start_mode: 'Start mode',
  account: 'Account',
  program: 'Program',
  hive: 'Hive',
  key_path: 'Key path',
  value_name: 'Value name',
  value: 'Value',
  version: 'Version',
};

type SeverityFilter = 'all' | 'high' | 'medium' | 'low';
type AlertDetail = Record<string, unknown>;

function parseDetail(raw?: string | null): AlertDetail | null {
  if (!raw?.trim()) return null;
  try {
    const parsed = JSON.parse(raw);
    if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
      return parsed as AlertDetail;
    }
  } catch {
    return null;
  }
  return null;
}

function formatDetailValue(value: unknown): string {
  if (Array.isArray(value)) return value.map(String).join(', ');
  if (value == null) return '';
  return String(value);
}

function CmdlineBlock({ label, value }: { label: string; value: string }) {
  return (
    <Box>
      <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
        {label}
      </Typography>
      <Typography
        variant="body2"
        component="pre"
        sx={{
          m: 0,
          mt: 0.25,
          p: 1,
          fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
          fontSize: '0.75rem',
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-word',
          bgcolor: 'background.paper',
          borderRadius: 1,
          border: 1,
          borderColor: 'divider',
        }}
      >
        {value}
      </Typography>
    </Box>
  );
}

function ProcessChainView({ detail }: { detail: AlertDetail }) {
  const parent = detail.parent_comm != null ? String(detail.parent_comm) : null;
  const child = detail.child_comm != null ? String(detail.child_comm) : null;
  const parentCmd = detail.parent_cmdline != null ? String(detail.parent_cmdline).trim() : '';
  const childCmd = detail.child_cmdline != null ? String(detail.child_cmdline).trim() : '';
  const singleCmd = detail.cmdline != null ? String(detail.cmdline).trim() : '';
  if (!parent && !child && !singleCmd) return null;

  return (
    <Stack spacing={1}>
      {parent && child && (
        <>
          <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
            Process chain
          </Typography>
          <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap>
            <Chip
              label={`${parent}${detail.parent_pid != null ? ` (pid ${detail.parent_pid})` : ''}`}
              size="small"
              variant="outlined"
            />
            <ArrowForwardIcon fontSize="small" color="action" />
            <Chip
              label={`${child}${detail.child_pid != null ? ` (pid ${detail.child_pid})` : ''}`}
              size="small"
              color="warning"
              variant="outlined"
            />
          </Stack>
        </>
      )}
      {parentCmd ? <CmdlineBlock label="Parent command" value={parentCmd} /> : null}
      {childCmd ? <CmdlineBlock label="Child command" value={childCmd} /> : null}
      {!parentCmd && !childCmd && singleCmd ? <CmdlineBlock label="Command" value={singleCmd} /> : null}
    </Stack>
  );
}

type ProcessSample = {
  pid: string;
  ppid: string | null;
  comm: string;
  executable: string;
  cmdline: string;
};

function processSampleFromUnknown(item: unknown): ProcessSample {
  const row = item && typeof item === 'object' ? (item as Record<string, unknown>) : {};
  return {
    pid: row.pid != null ? String(row.pid) : '?',
    ppid: row.ppid != null ? String(row.ppid) : null,
    comm: row.comm != null ? String(row.comm) : 'unknown',
    executable: row.executable != null ? String(row.executable).trim() : '',
    cmdline: row.cmdline != null ? String(row.cmdline).trim() : '',
  };
}

function processRowsForGraph(rows: ProcessSample[], selectedComm: string | null): ProcessSample[] {
  if (!selectedComm) return rows;
  const byPid = new Map(rows.map((row) => [row.pid, row]));
  const keep = new Set<string>();
  for (const row of rows) {
    if (row.comm !== selectedComm) continue;
    let current: ProcessSample | undefined = row;
    while (current && !keep.has(current.pid)) {
      keep.add(current.pid);
      current = current.ppid ? byPid.get(current.ppid) : undefined;
    }
  }
  return rows.filter((row) => keep.has(row.pid));
}

type GraphNode = {
  pid: string;
  ppid: string | null;
  comm: string;
  synthetic: boolean;
  depth: number;
  row: number;
  x: number;
  y: number;
};

const NODE_W = 168;
const NODE_H = 34;
const H_GAP = 56;
const V_GAP = 14;

function buildProcessGraph(rows: ProcessSample[]): {
  nodes: GraphNode[];
  edges: Array<{ from: GraphNode; to: GraphNode }>;
  width: number;
  height: number;
} {
  const nodes = new Map<string, GraphNode>();
  const makeNode = (pid: string, comm: string, ppid: string | null, synthetic: boolean) => {
    const existing = nodes.get(pid);
    if (existing) {
      if (synthetic === false && existing.synthetic) {
        existing.synthetic = false;
        existing.comm = comm;
        existing.ppid = ppid;
      }
      return existing;
    }
    const node: GraphNode = { pid, ppid, comm, synthetic, depth: 0, row: 0, x: 0, y: 0 };
    nodes.set(pid, node);
    return node;
  };

  for (const r of rows) makeNode(r.pid, r.comm, r.ppid, false);
  // Synthesize any referenced parent that was not itself sampled.
  for (const r of rows) {
    if (r.ppid && !nodes.has(r.ppid)) {
      makeNode(r.ppid, `pid ${r.ppid}`, null, true);
    }
  }

  const childrenByParent = new Map<string, GraphNode[]>();
  const roots: GraphNode[] = [];
  for (const node of nodes.values()) {
    if (node.ppid && nodes.has(node.ppid)) {
      const list = childrenByParent.get(node.ppid) || [];
      list.push(node);
      childrenByParent.set(node.ppid, list);
    } else {
      roots.push(node);
    }
  }
  for (const list of childrenByParent.values()) {
    list.sort((a, b) => Number(a.pid) - Number(b.pid));
  }
  roots.sort((a, b) => Number(a.pid) - Number(b.pid));

  // DFS assigns depth (column) and a sequential row so the layout reads top-down.
  let rowCounter = 0;
  let maxDepth = 0;
  const visited = new Set<string>();
  const walk = (node: GraphNode, depth: number) => {
    if (visited.has(node.pid)) return;
    visited.add(node.pid);
    node.depth = depth;
    node.row = rowCounter++;
    maxDepth = Math.max(maxDepth, depth);
    for (const child of childrenByParent.get(node.pid) || []) walk(child, depth + 1);
  };
  for (const root of roots) walk(root, 0);

  const nodeList = Array.from(nodes.values());
  for (const node of nodeList) {
    node.x = node.depth * (NODE_W + H_GAP);
    node.y = node.row * (NODE_H + V_GAP);
  }

  const edges: Array<{ from: GraphNode; to: GraphNode }> = [];
  for (const node of nodeList) {
    if (node.ppid && nodes.has(node.ppid)) {
      edges.push({ from: nodes.get(node.ppid) as GraphNode, to: node });
    }
  }

  const width = (maxDepth + 1) * NODE_W + maxDepth * H_GAP;
  const height = Math.max(rowCounter, 1) * NODE_H + Math.max(rowCounter - 1, 0) * V_GAP;
  return { nodes: nodeList, edges, width, height };
}

function ProcessGraphView({ rows, selectedComm }: { rows: ProcessSample[]; selectedComm: string | null }) {
  const graph = useMemo(() => buildProcessGraph(rows), [rows]);
  if (rows.length === 0) return null;
  const { nodes, edges, width, height } = graph;

  return (
    <Box sx={{ mb: 1 }}>
      <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
        Process graph
        {selectedComm ? ' (matching processes plus sampled ancestors)' : ''}
      </Typography>
      <Box
        sx={{
          mt: 0.5,
          p: 1,
          borderRadius: 1,
          border: 1,
          borderColor: 'divider',
          bgcolor: 'background.paper',
          overflow: 'auto',
          maxHeight: 360,
        }}
      >
        <svg
          width={width}
          height={height}
          viewBox={`0 0 ${width} ${height}`}
          style={{ display: 'block', minWidth: '100%' }}
        >
          {edges.map((edge) => {
            const x1 = edge.from.x + NODE_W;
            const y1 = edge.from.y + NODE_H / 2;
            const x2 = edge.to.x;
            const y2 = edge.to.y + NODE_H / 2;
            const midX = (x1 + x2) / 2;
            return (
              <path
                key={`${edge.from.pid}->${edge.to.pid}`}
                d={`M ${x1} ${y1} C ${midX} ${y1}, ${midX} ${y2}, ${x2} ${y2}`}
                fill="none"
                stroke="currentColor"
                strokeOpacity={0.35}
                strokeWidth={1.5}
              />
            );
          })}
          {nodes.map((node) => {
            const selected = !node.synthetic && selectedComm === node.comm;
            return (
              <g key={node.pid} transform={`translate(${node.x}, ${node.y})`}>
                <rect
                  width={NODE_W}
                  height={NODE_H}
                  rx={6}
                  ry={6}
                  fill={selected ? 'rgba(237, 108, 2, 0.16)' : 'transparent'}
                  stroke="currentColor"
                  strokeOpacity={node.synthetic ? 0.4 : 0.75}
                  strokeDasharray={node.synthetic ? '4 3' : undefined}
                  strokeWidth={selected ? 2 : 1}
                />
                <text
                  x={8}
                  y={14}
                  fontSize={11}
                  fontWeight={600}
                  fill="currentColor"
                  fontFamily="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace"
                >
                  {node.comm.length > 22 ? `${node.comm.slice(0, 21)}…` : node.comm}
                </text>
                <text
                  x={8}
                  y={27}
                  fontSize={10}
                  fill="currentColor"
                  fillOpacity={0.7}
                  fontFamily="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace"
                >
                  {node.synthetic ? `pid ${node.pid} · parent` : `pid ${node.pid}`}
                </text>
              </g>
            );
          })}
        </svg>
      </Box>
    </Box>
  );
}

function ProcessBurstView({ detail }: { detail: AlertDetail }) {
  const processes = Array.isArray(detail.processes) ? detail.processes : [];
  const topComms = Array.isArray(detail.top_comms) ? detail.top_comms : [];
  const [selectedComm, setSelectedComm] = useState<string | null>(null);
  if (processes.length === 0 && topComms.length === 0) return null;

  const processRows = processes.map(processSampleFromUnknown);
  const visibleProcesses = selectedComm ? processRows.filter((row) => row.comm === selectedComm) : processRows;
  const graphProcesses = processRowsForGraph(processRows, selectedComm);

  return (
    <Stack spacing={1}>
      {topComms.length > 0 ? (
        <Box>
          <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
            Top processes
            {selectedComm ? ` · filtered to ${selectedComm}` : ' · click to filter'}
          </Typography>
          <Stack direction="row" spacing={0.75} flexWrap="wrap" useFlexGap sx={{ mt: 0.5 }}>
            {topComms.map((item, index) => {
              const row = item && typeof item === 'object' ? (item as Record<string, unknown>) : {};
              const comm = row.comm != null ? String(row.comm) : 'unknown';
              const count = row.count != null ? String(row.count) : '?';
              const selected = selectedComm === comm;
              return (
                <Chip
                  key={`${comm}-${index}`}
                  label={`${comm} ×${count}`}
                  size="small"
                  clickable
                  color={selected ? 'warning' : 'default'}
                  variant={selected ? 'filled' : 'outlined'}
                  onClick={(event) => {
                    event.stopPropagation();
                    setSelectedComm((current) => (current === comm ? null : comm));
                  }}
                  onDelete={
                    selected
                      ? (event) => {
                          event.stopPropagation();
                          setSelectedComm(null);
                        }
                      : undefined
                  }
                />
              );
            })}
          </Stack>
        </Box>
      ) : null}
      {processes.length > 0 ? (
        <Box>
          <ProcessGraphView rows={graphProcesses} selectedComm={selectedComm} />
          <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
            Recent processes
            {selectedComm
              ? ` (showing ${visibleProcesses.length} matching ${selectedComm})`
              : detail.count != null
                ? ` (showing ${visibleProcesses.length} of ${String(detail.count)})`
                : ` (${visibleProcesses.length})`}
          </Typography>
          <Stack spacing={0.75} sx={{ mt: 0.5 }}>
            {visibleProcesses.length === 0 ? (
              <Typography variant="body2" color="text.secondary">
                No sampled processes match this filter.
              </Typography>
            ) : (
              visibleProcesses.map((row, index) => {
                return (
                  <Box
                    key={`${row.pid}-${index}`}
                    sx={{
                      p: 1,
                      borderRadius: 1,
                      border: 1,
                      borderColor: 'divider',
                      bgcolor: 'background.paper',
                    }}
                  >
                    <Typography
                      variant="body2"
                      sx={{
                        fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
                        fontSize: '0.75rem',
                        fontWeight: 600,
                      }}
                    >
                      {row.comm}
                      {` (pid ${row.pid}`}
                      {row.ppid ? `, ppid ${row.ppid}` : ''}
                      {`)`}
                    </Typography>
                    {row.executable ? (
                      <Typography
                        variant="caption"
                        color="text.secondary"
                        sx={{
                          display: 'block',
                          fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
                        }}
                      >
                        {row.executable}
                      </Typography>
                    ) : null}
                    {row.cmdline ? (
                      <Typography
                        variant="caption"
                        component="pre"
                        sx={{
                          m: 0,
                          mt: 0.5,
                          fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
                          fontSize: '0.7rem',
                          whiteSpace: 'pre-wrap',
                          wordBreak: 'break-word',
                        }}
                      >
                        {row.cmdline}
                      </Typography>
                    ) : null}
                  </Box>
                );
              })
            )}
          </Stack>
        </Box>
      ) : null}
    </Stack>
  );
}

function DetailFields({ detail }: { detail: AlertDetail }) {
  const chainKeys = new Set([
    'parent_comm',
    'child_comm',
    'parent_pid',
    'child_pid',
    'parent_cmdline',
    'child_cmdline',
    'cmdline',
    'processes',
    'top_comms',
    'sample_limit',
  ]);
  const entries = Object.entries(detail).filter(([key, value]) => !chainKeys.has(key) && value != null);
  if (entries.length === 0) return null;

  return (
    <Stack spacing={0.75}>
      <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
        Related evidence
      </Typography>
      <Box
        component="dl"
        sx={{
          m: 0,
          display: 'grid',
          gridTemplateColumns: 'max-content 1fr',
          columnGap: 1.5,
          rowGap: 0.5,
        }}
      >
        {entries.map(([key, value]) => (
          <Box key={key} sx={{ display: 'contents' }}>
            <Typography
              component="dt"
              variant="caption"
              color="text.secondary"
              sx={{ fontWeight: 600 }}
            >
              {DETAIL_LABELS[key] || key.replace(/_/g, ' ')}
            </Typography>
            <Typography
              component="dd"
              variant="body2"
              sx={{
                m: 0,
                fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
                fontSize: '0.75rem',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
              }}
            >
              {formatDetailValue(value)}
            </Typography>
          </Box>
        ))}
      </Box>
    </Stack>
  );
}

function MetaField({ label, value, mono = false }: { label: string; value: string; mono?: boolean }) {
  return (
    <Typography variant="caption" color="text.secondary" component="span" sx={{ display: 'inline-flex', gap: 0.5 }}>
      <Box component="span" sx={{ color: 'text.disabled', fontWeight: 600 }}>
        {label}
      </Box>
      <Box component="span" sx={mono ? { fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace' } : undefined}>
        {value}
      </Box>
    </Typography>
  );
}

function AlertMetadata({ alert }: { alert: SecurityAlert }) {
  const entries: Array<[string, string]> = [
    ['Device', alert.device_id],
    ...(alert.event_type ? [['Event', alert.event_type] as [string, string]] : []),
    ...(alert.event_id ? [['Event ID', alert.event_id] as [string, string]] : []),
  ];

  if (entries.length === 0) return null;

  return (
    <Stack spacing={0.75}>
      <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
        Alert metadata
      </Typography>
      <Box
        component="dl"
        sx={{
          m: 0,
          display: 'grid',
          gridTemplateColumns: 'max-content 1fr',
          columnGap: 1.5,
          rowGap: 0.5,
        }}
      >
        {entries.map(([key, value]) => (
          <Box key={key} sx={{ display: 'contents' }}>
            <Typography component="dt" variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
              {key}
            </Typography>
            <Typography
              component="dd"
              variant="body2"
              sx={{
                m: 0,
                fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
                fontSize: '0.75rem',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
              }}
            >
              {value}
            </Typography>
          </Box>
        ))}
      </Box>
    </Stack>
  );
}

function AlertRow({
  alert,
  expanded,
  onToggle,
}: {
  alert: SecurityAlert;
  expanded: boolean;
  onToggle: () => void;
}) {
  const label = TYPE_LABEL[alert.alert_type] || alert.alert_type.replace(/_/g, ' ');
  const severity = SEVERITY_COLOR[alert.severity] || 'default';
  const detail = parseDetail(alert.detail);
  const hasDetail = detail != null;
  const hasMetadata = Boolean(alert.device_id || alert.event_type || alert.event_id);
  const canExpand = hasDetail || hasMetadata;
  const [explaining, setExplaining] = useState(false);
  const [explanation, setExplanation] = useState<string | null>(null);
  const [explainModel, setExplainModel] = useState<string | null>(null);
  const [explainError, setExplainError] = useState<string | null>(null);

  const handleExplain = async (event: MouseEvent) => {
    event.stopPropagation();
    setExplaining(true);
    setExplainError(null);
    try {
      const result = await twinApi.explainAlert(alert);
      setExplanation(result.explanation);
      setExplainModel(result.model);
    } catch (err) {
      setExplanation(null);
      setExplainModel(null);
      setExplainError(err instanceof Error ? err.message : 'Failed to explain alert');
    } finally {
      setExplaining(false);
    }
  };

  return (
    <Box>
      <ListItemButton onClick={canExpand ? onToggle : undefined} sx={{ py: 1, px: 2, alignItems: 'flex-start' }}>
        <ListItemText
          primary={
            <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap>
              <Chip label={label} size="small" color={severity} variant="outlined" />
              <Chip label={alert.severity} size="small" color={severity} />
              <Typography variant="body2" sx={{ fontWeight: 600, flex: 1, minWidth: 160 }}>
                {alert.message || label}
              </Typography>
              {canExpand && (expanded ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />)}
            </Stack>
          }
          secondary={
            <Stack direction="row" spacing={1.5} alignItems="center" flexWrap="wrap" useFlexGap sx={{ mt: 0.5 }}>
              <MetaField label="Time" value={formatShortDateTime(alert.timestamp)} />
            </Stack>
          }
        />
      </ListItemButton>
      {canExpand && (
        <Collapse in={expanded} timeout="auto" unmountOnExit>
          <Box sx={{ px: 2, pb: 1.5, pt: 0.5 }}>
            <Paper variant="outlined" sx={{ p: 1.5, bgcolor: 'action.hover' }}>
              <Stack spacing={1.5}>
                <AlertMetadata alert={alert} />
                {detail ? <ProcessChainView detail={detail} /> : null}
                {detail ? <ProcessBurstView detail={detail} /> : null}
                {detail ? <DetailFields detail={detail} /> : null}
                <Stack direction="row" spacing={1} alignItems="center">
                  <Button
                    size="small"
                    variant="outlined"
                    startIcon={explaining ? <CircularProgress size={14} /> : <AutoAwesomeIcon />}
                    onClick={handleExplain}
                    disabled={explaining}
                  >
                    {explaining ? 'Explaining…' : 'Explain with Ollama'}
                  </Button>
                  {explainModel ? (
                    <Typography variant="caption" color="text.secondary">
                      Model: {explainModel}
                    </Typography>
                  ) : null}
                </Stack>
                {explainError ? (
                  <Alert severity="error" onClose={() => setExplainError(null)}>
                    {explainError}
                  </Alert>
                ) : null}
                {explanation ? (
                  <Box>
                    <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
                      AI explanation
                    </Typography>
                    <Typography
                      variant="body2"
                      sx={{ mt: 0.5, whiteSpace: 'pre-wrap', lineHeight: 1.55 }}
                    >
                      {explanation}
                    </Typography>
                  </Box>
                ) : null}
              </Stack>
            </Paper>
          </Box>
        </Collapse>
      )}
    </Box>
  );
}

export default function AlertsPage() {
  const [severityFilter, setSeverityFilter] = useState<SeverityFilter>('all');
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const severityParam = severityFilter === 'all' ? undefined : severityFilter;
  const { items, total, loading, refetch } = useSecurityAlerts({
    pageSize: 100,
    severity: severityParam,
  });

  const emptyCopy = useMemo(() => {
    if (severityFilter === 'all') {
      return 'No detection alerts yet. When the rules engine fires, findings appear here.';
    }
    return `No ${severityFilter}-severity alerts yet.`;
  }, [severityFilter]);

  return (
    <Box sx={{ width: '100%', maxWidth: { sm: '100%', md: '1700px' } }}>
      <Stack
        direction={{ xs: 'column', sm: 'row' }}
        spacing={1.5}
        alignItems={{ xs: 'stretch', sm: 'center' }}
        justifyContent="space-between"
        sx={{ mb: 2 }}
      >
        <Box>
          <Typography component="h1" variant="h5" sx={{ mb: 0.5 }}>
            Alerts
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Detection findings from the rules engine (all severities). Expand an alert to see linked
            process or network evidence.
          </Typography>
        </Box>
        <Stack direction="row" spacing={1} alignItems="center" justifyContent="flex-end">
          <ToggleButtonGroup
            size="small"
            exclusive
            value={severityFilter}
            onChange={(_event, value: SeverityFilter | null) => {
              if (value) setSeverityFilter(value);
            }}
          >
            <ToggleButton value="all">All</ToggleButton>
            <ToggleButton value="high">High</ToggleButton>
            <ToggleButton value="medium">Medium</ToggleButton>
            <ToggleButton value="low">Low</ToggleButton>
          </ToggleButtonGroup>
          {total > 0 && <Chip label={total} size="small" variant="outlined" />}
          <Tooltip title="Refresh">
            <span>
              <IconButton size="small" onClick={refetch} disabled={loading}>
                <RefreshIcon fontSize="small" />
              </IconButton>
            </span>
          </Tooltip>
        </Stack>
      </Stack>

      <Paper variant="outlined">
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
            <CircularProgress size={28} />
          </Box>
        ) : items.length === 0 ? (
          <Typography color="text.secondary" sx={{ p: 3 }}>
            {emptyCopy}
          </Typography>
        ) : (
          <List dense disablePadding>
            {items.map((alert, index) => (
              <Box key={alert.id}>
                <AlertRow
                  alert={alert}
                  expanded={expandedId === alert.id}
                  onToggle={() => setExpandedId((current) => (current === alert.id ? null : alert.id))}
                />
                {index < items.length - 1 && <Divider component="li" />}
              </Box>
            ))}
          </List>
        )}
      </Paper>
    </Box>
  );
}
