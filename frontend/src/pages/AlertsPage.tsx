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

function ProcessBurstView({ detail }: { detail: AlertDetail }) {
  const processes = Array.isArray(detail.processes) ? detail.processes : [];
  const topComms = Array.isArray(detail.top_comms) ? detail.top_comms : [];
  if (processes.length === 0 && topComms.length === 0) return null;

  return (
    <Stack spacing={1}>
      {topComms.length > 0 ? (
        <Box>
          <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
            Top processes
          </Typography>
          <Stack direction="row" spacing={0.75} flexWrap="wrap" useFlexGap sx={{ mt: 0.5 }}>
            {topComms.map((item, index) => {
              const row = item && typeof item === 'object' ? (item as Record<string, unknown>) : {};
              const comm = row.comm != null ? String(row.comm) : 'unknown';
              const count = row.count != null ? String(row.count) : '?';
              return (
                <Chip
                  key={`${comm}-${index}`}
                  label={`${comm} ×${count}`}
                  size="small"
                  variant="outlined"
                />
              );
            })}
          </Stack>
        </Box>
      ) : null}
      {processes.length > 0 ? (
        <Box>
          <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
            Recent processes
            {detail.count != null
              ? ` (showing ${processes.length} of ${String(detail.count)})`
              : ` (${processes.length})`}
          </Typography>
          <Stack spacing={0.75} sx={{ mt: 0.5 }}>
            {processes.map((item, index) => {
              const row = item && typeof item === 'object' ? (item as Record<string, unknown>) : {};
              const comm = row.comm != null ? String(row.comm) : 'unknown';
              const pid = row.pid != null ? String(row.pid) : '?';
              const ppid = row.ppid != null ? String(row.ppid) : null;
              const cmdline = row.cmdline != null ? String(row.cmdline).trim() : '';
              const executable = row.executable != null ? String(row.executable).trim() : '';
              return (
                <Box
                  key={`${pid}-${index}`}
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
                    {comm}
                    {` (pid ${pid}`}
                    {ppid ? `, ppid ${ppid}` : ''}
                    {`)`}
                  </Typography>
                  {executable ? (
                    <Typography
                      variant="caption"
                      color="text.secondary"
                      sx={{
                        display: 'block',
                        fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
                      }}
                    >
                      {executable}
                    </Typography>
                  ) : null}
                  {cmdline ? (
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
                      {cmdline}
                    </Typography>
                  ) : null}
                </Box>
              );
            })}
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
