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
  eventId: string;
  pid: string;
  ppid: string | null;
  comm: string;
  parentComm: string;
  executable: string;
  cmdline: string;
  startedAt: string;
  role: string;
};

function processSampleFromUnknown(item: unknown): ProcessSample {
  const row = item && typeof item === 'object' ? (item as Record<string, unknown>) : {};
  return {
    eventId: row.event_id != null ? String(row.event_id) : '',
    pid: row.pid != null ? String(row.pid) : '?',
    ppid: row.ppid != null ? String(row.ppid) : null,
    comm: row.comm != null ? String(row.comm) : 'unknown',
    parentComm: row.parent_comm != null ? String(row.parent_comm) : '',
    executable: row.executable != null ? String(row.executable).trim() : '',
    cmdline: row.cmdline != null ? String(row.cmdline).trim() : '',
    startedAt: row.started_at != null ? String(row.started_at) : '',
    role: row.role != null ? String(row.role) : 'context',
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

/** Best available name for a parent PID that was not itself sampled. */
function syntheticParentLabel(ppid: string, rows: ProcessSample[]): string {
  const votes = new Map<string, number>();
  for (const row of rows) {
    if (row.ppid !== ppid || !row.parentComm) continue;
    const name = row.parentComm.trim();
    if (!name) continue;
    votes.set(name, (votes.get(name) || 0) + 1);
  }
  let best = '';
  let bestCount = 0;
  for (const [name, count] of votes) {
    if (count > bestCount || (count === bestCount && name.localeCompare(best) < 0)) {
      best = name;
      bestCount = count;
    }
  }
  if (best) return best;
  // PID 1 is the system init process on Unix-like hosts (launchd / systemd / init).
  if (ppid === '1') return 'init';
  return `pid ${ppid}`;
}

type GraphGroup = {
  id: string;
  comm: string;
  pids: string[];
  triggerPids: string[];
  synthetic: boolean;
  depth: number;
  row: number;
  x: number;
  y: number;
  height: number;
};

const NODE_W = 180;
const H_GAP = 64;
const V_GAP = 18;
const HEADER_H = 18;
const PID_LINE_H = 12;
const NODE_PAD = 8;
const MAX_PIDS_SHOWN = 8;

function groupNodeHeight(pidCount: number): number {
  const shown = Math.min(pidCount, MAX_PIDS_SHOWN) + (pidCount > MAX_PIDS_SHOWN ? 1 : 0);
  return HEADER_H + shown * PID_LINE_H + NODE_PAD;
}

function buildProcessGraph(rows: ProcessSample[]): {
  nodes: GraphGroup[];
  edges: Array<{ from: GraphGroup; to: GraphGroup }>;
  width: number;
  height: number;
} {
  const groups = new Map<string, GraphGroup>();
  const pidToGroup = new Map<string, string>();

  const ensureGroup = (id: string, comm: string, synthetic: boolean) => {
    let group = groups.get(id);
    if (!group) {
      group = {
        id,
        comm,
        pids: [],
        triggerPids: [],
        synthetic,
        depth: 0,
        row: 0,
        x: 0,
        y: 0,
        height: groupNodeHeight(0),
      };
      groups.set(id, group);
    } else if (!synthetic && group.synthetic) {
      group.synthetic = false;
      group.comm = comm;
    }
    return group;
  };

  for (const r of rows) {
    const id = `comm:${r.comm}`;
    const group = ensureGroup(id, r.comm, false);
    if (!group.pids.includes(r.pid)) group.pids.push(r.pid);
    if (r.role === 'trigger' && !group.triggerPids.includes(r.pid)) group.triggerPids.push(r.pid);
    pidToGroup.set(r.pid, id);
  }

  // Synthesize missing parents as their own groups so edges still exist.
  for (const r of rows) {
    if (!r.ppid || pidToGroup.has(r.ppid)) continue;
    const id = `parent:${r.ppid}`;
    const group = ensureGroup(id, syntheticParentLabel(r.ppid, rows), true);
    if (!group.pids.includes(r.ppid)) group.pids.push(r.ppid);
    pidToGroup.set(r.ppid, id);
  }

  for (const group of groups.values()) {
    group.pids.sort((a, b) => Number(a) - Number(b));
    group.height = groupNodeHeight(group.pids.length);
  }

  const edgeKeys = new Set<string>();
  const childrenByParent = new Map<string, string[]>();
  for (const r of rows) {
    if (!r.ppid) continue;
    const parentId = pidToGroup.get(r.ppid);
    const childId = pidToGroup.get(r.pid);
    if (!parentId || !childId || parentId === childId) continue;
    const key = `${parentId}->${childId}`;
    if (edgeKeys.has(key)) continue;
    edgeKeys.add(key);
    const list = childrenByParent.get(parentId) || [];
    list.push(childId);
    childrenByParent.set(parentId, list);
  }

  const childIds = new Set<string>();
  for (const children of childrenByParent.values()) {
    for (const id of children) childIds.add(id);
  }
  const roots = Array.from(groups.keys())
    .filter((id) => !childIds.has(id))
    .sort((a, b) => a.localeCompare(b));

  // DFS on the grouped DAG: column = depth, vertical order = visit order.
  let maxDepth = 0;
  const visited = new Set<string>();
  const order: string[] = [];
  const walk = (id: string, depth: number) => {
    if (visited.has(id)) return;
    visited.add(id);
    const group = groups.get(id);
    if (!group) return;
    group.depth = depth;
    maxDepth = Math.max(maxDepth, depth);
    order.push(id);
    for (const childId of childrenByParent.get(id) || []) walk(childId, depth + 1);
  };
  for (const root of roots) walk(root, 0);
  for (const id of groups.keys()) {
    if (!visited.has(id)) walk(id, 0);
  }

  // Place each depth column independently so siblings stack tightly.
  const byDepth = new Map<number, GraphGroup[]>();
  for (const id of order) {
    const group = groups.get(id);
    if (!group) continue;
    const list = byDepth.get(group.depth) || [];
    list.push(group);
    byDepth.set(group.depth, list);
  }

  let maxHeight = 0;
  for (const [depth, list] of byDepth) {
    let y = 0;
    for (const group of list) {
      group.x = depth * (NODE_W + H_GAP);
      group.y = y;
      y += group.height + V_GAP;
    }
    maxHeight = Math.max(maxHeight, y - V_GAP);
  }

  const edges: Array<{ from: GraphGroup; to: GraphGroup }> = [];
  for (const key of edgeKeys) {
    const [fromId, toId] = key.split('->');
    const from = groups.get(fromId);
    const to = groups.get(toId);
    if (from && to) edges.push({ from, to });
  }

  const width = (maxDepth + 1) * NODE_W + maxDepth * H_GAP;
  const height = Math.max(maxHeight, groupNodeHeight(1));
  return { nodes: Array.from(groups.values()), edges, width, height };
}

function ProcessGraphView({ rows, selectedComm }: { rows: ProcessSample[]; selectedComm: string | null }) {
  const graph = useMemo(() => buildProcessGraph(rows), [rows]);
  if (rows.length === 0) return null;
  const { nodes, edges, width, height } = graph;

  return (
    <Box sx={{ mb: 1 }}>
      <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
        Process graph
        {selectedComm ? ' (matching processes plus sampled ancestors)' : ' · grouped by command'}
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
          maxHeight: 420,
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
            const y1 = edge.from.y + edge.from.height / 2;
            const x2 = edge.to.x;
            const y2 = edge.to.y + edge.to.height / 2;
            const midX = (x1 + x2) / 2;
            return (
              <path
                key={`${edge.from.id}->${edge.to.id}`}
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
            const triggered = node.triggerPids.length > 0;
            const shown = node.pids.slice(0, MAX_PIDS_SHOWN);
            const hidden = node.pids.length - shown.length;
            return (
              <g key={node.id} transform={`translate(${node.x}, ${node.y})`}>
                <rect
                  width={NODE_W}
                  height={node.height}
                  rx={6}
                  ry={6}
                  fill={triggered ? 'rgba(211, 47, 47, 0.14)' : selected ? 'rgba(237, 108, 2, 0.16)' : 'transparent'}
                  stroke={triggered ? '#d32f2f' : 'currentColor'}
                  strokeOpacity={node.synthetic ? 0.4 : 0.75}
                  strokeDasharray={node.synthetic ? '4 3' : undefined}
                  strokeWidth={triggered || selected ? 2 : 1}
                />
                <text
                  x={8}
                  y={14}
                  fontSize={11}
                  fontWeight={600}
                  fill="currentColor"
                  fontFamily="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace"
                >
                  {(node.comm.length > 22 ? `${node.comm.slice(0, 21)}…` : node.comm) +
                    (node.synthetic ? '' : ` ×${node.pids.length}${triggered ? ' · source' : ''}`)}
                </text>
                {shown.map((pid, index) => (
                  <text
                    key={pid}
                    x={8}
                    y={HEADER_H + (index + 1) * PID_LINE_H}
                    fontSize={10}
                    fill="currentColor"
                    fillOpacity={0.7}
                    fontFamily="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace"
                  >
                    {node.synthetic
                      ? `pid ${pid} · parent`
                      : `pid ${pid}${node.triggerPids.includes(pid) ? ' · source' : ''}`}
                  </text>
                ))}
                {hidden > 0 ? (
                  <text
                    x={8}
                    y={HEADER_H + (shown.length + 1) * PID_LINE_H}
                    fontSize={10}
                    fill="currentColor"
                    fillOpacity={0.55}
                    fontFamily="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace"
                  >
                    +{hidden} more
                  </text>
                ) : null}
              </g>
            );
          })}
        </svg>
      </Box>
    </Box>
  );
}

function SourceEventView({ detail }: { detail: AlertDetail }) {
  const raw = detail.source_event;
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return null;
  const source = raw as Record<string, unknown>;
  const type = source.type != null ? String(source.type) : '';
  const timestamp = source.timestamp != null ? String(source.timestamp) : '';
  const eventId = source.event_id != null ? String(source.event_id) : '';
  if (!type && !timestamp && !eventId) return null;

  return (
    <Stack spacing={0.5}>
      <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
        Source event
      </Typography>
      <Stack direction="row" spacing={0.75} alignItems="center" flexWrap="wrap" useFlexGap>
        {type ? <Chip label={type} size="small" color="error" variant="outlined" /> : null}
        {timestamp ? <Chip label={formatShortDateTime(timestamp)} size="small" variant="outlined" /> : null}
        {eventId ? (
          <Typography
            variant="caption"
            color="text.secondary"
            sx={{ fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace' }}
          >
            {eventId}
          </Typography>
        ) : null}
      </Stack>
    </Stack>
  );
}

function ProcessContextView({ detail }: { detail: AlertDetail }) {
  const processes = Array.isArray(detail.processes) ? detail.processes : [];
  const topComms = Array.isArray(detail.top_comms) ? detail.top_comms : [];
  const [selectedComm, setSelectedComm] = useState<string | null>(null);
  if (processes.length === 0 && topComms.length === 0) return null;

  const processRows = processes.map(processSampleFromUnknown);
  const visibleProcesses = selectedComm ? processRows.filter((row) => row.comm === selectedComm) : processRows;
  const graphProcesses = processRowsForGraph(processRows, selectedComm);
  const contextKind = detail.process_context_kind != null ? String(detail.process_context_kind) : '';
  const processSummary =
    contextKind === 'ancestry'
      ? ` (${visibleProcesses.length} related process${visibleProcesses.length === 1 ? '' : 'es'})`
      : detail.count != null
        ? ` (showing ${visibleProcesses.length} of ${String(detail.count)})`
        : ` (${visibleProcesses.length})`;

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
            Process timeline
            {selectedComm
              ? ` (showing ${visibleProcesses.length} matching ${selectedComm})`
              : processSummary}
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
                      {row.ppid
                        ? `, ppid ${row.ppid}${row.parentComm ? ` ${row.parentComm}` : ''}`
                        : ''}
                      {`)`}
                    </Typography>
                    <Stack direction="row" spacing={0.75} alignItems="center" flexWrap="wrap" useFlexGap>
                      {row.role === 'trigger' ? <Chip label="Source" size="small" color="error" /> : null}
                      {row.startedAt ? (
                        <Typography variant="caption" color="text.secondary">
                          {formatShortDateTime(row.startedAt)}
                        </Typography>
                      ) : null}
                    </Stack>
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
    'source_event',
    'process_context_kind',
    'process_context_window_minutes',
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
                {detail ? <SourceEventView detail={detail} /> : null}
                {detail ? <ProcessChainView detail={detail} /> : null}
                {detail ? <ProcessContextView detail={detail} /> : null}
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
          <Typography
            component="h1"
            sx={{
              fontWeight: 700,
              fontSize: { xs: '1.5rem', md: '1.75rem' },
              letterSpacing: '-0.03em',
              color: 'text.primary',
              lineHeight: 1.2,
              mb: 0.75,
            }}
          >
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
