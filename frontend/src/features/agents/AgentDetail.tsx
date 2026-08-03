import { Link as RouterLink } from 'react-router-dom';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Paper from '@mui/material/Paper';
import Stack from '@mui/material/Stack';
import Button from '@mui/material/Button';
import Chip from '@mui/material/Chip';
import CircularProgress from '@mui/material/CircularProgress';
import Alert from '@mui/material/Alert';
import Grid from '@mui/material/Grid';
import Divider from '@mui/material/Divider';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemText from '@mui/material/ListItemText';
import IconButton from '@mui/material/IconButton';
import Tooltip from '@mui/material/Tooltip';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import RefreshIcon from '@mui/icons-material/Refresh';
import FormControlLabel from '@mui/material/FormControlLabel';
import Switch from '@mui/material/Switch';
import { useMemo, useState } from 'react';
import { useAgentDetail } from './hooks/useAgentDetail';
import { useSecurityAlerts } from '../twin/hooks/useSecurityAlerts';
import { useDeviceBaseline } from '../twin/hooks/useDeviceBaseline';
import { isAgentOnline } from './utils/presence';
import {
  displayBaselineKey,
  prepareBaselineItems,
} from './utils/baselineDisplay';
import { formatShortDateTime } from '../../shared/utils/dateUtils';
import { AgentTelemetryEvent, ConnectedAgent } from '../twin/types/connectedAgent';
import { SecurityAlert } from '../twin/types/securityAlert';
import { DeviceBaselineItem, DeviceBaselineResponse } from '../twin/types/deviceBaseline';

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

const EVENT_TYPE_LABEL: Record<string, string> = {
  client_details: 'Client details',
  network_summary: 'Network summary',
  action_summary: 'Action summary',
  process_start: 'Process start',
  process_exit: 'Process exit',
  driver_load: 'Driver load',
  service_install: 'Service install',
  registry_persistence: 'Registry persistence',
};

function labelAlertType(alertType: string): string {
  return TYPE_LABEL[alertType] || alertType.replace(/_/g, ' ');
}

function labelEventType(type: string): string {
  return EVENT_TYPE_LABEL[type] || type.replace(/_/g, ' ');
}

function metric(value: string | number | null | undefined, fallback = '—'): string {
  if (value == null || value === '') return fallback;
  return String(value);
}

function summarizeEvent(event: AgentTelemetryEvent): string {
  const p = event.payload || {};
  if (event.type === 'process_start' || event.type === 'process_exit') {
    const comm = String(p.comm || p.executable || '').trim();
    const pid = p.pid != null ? `pid ${p.pid}` : '';
    return [comm, pid].filter(Boolean).join(' · ') || 'Process event';
  }
  if (event.type === 'network_summary') {
    const parts = [
      p.public_ip ? `IP ${p.public_ip}` : '',
      p.network_type ? String(p.network_type) : '',
      p.established_count != null ? `${p.established_count} established` : '',
    ].filter(Boolean);
    return parts.join(' · ') || 'Network posture';
  }
  if (event.type === 'action_summary') {
    const parts = [
      p.presence ? String(p.presence) : '',
      p.idle_sec != null ? `idle ${p.idle_sec}s` : '',
      p.app_switches != null ? `${p.app_switches} switches` : '',
    ].filter(Boolean);
    return parts.join(' · ') || 'Activity summary';
  }
  if (event.type === 'client_details') {
    return [p.hostname, p.os, p.agent_version].filter(Boolean).join(' · ') || 'Host details';
  }
  const name = String(p.display_name || p.name || p.path || p.value_name || '').trim();
  return name || 'Security lifecycle event';
}

function TelemetryCard({
  live,
  liveMissing,
}: {
  live: ConnectedAgent | null;
  liveMissing: boolean;
}) {
  if (liveMissing || !live) {
    return (
      <Alert severity="info" variant="outlined">
        No live twin telemetry yet. It appears after the agent posts events and Agent-API writes Redis
        state.
      </Alert>
    );
  }

  const rows: Array<[string, string]> = [
    ['Public IP', metric(live.public_ip)],
    ['Network', metric(live.network_type)],
    ['Listening', metric(live.listening_count)],
    ['Established', metric(live.established_count)],
    ['Presence', metric(live.presence)],
    ['Idle', live.idle_sec != null ? `${live.idle_sec}s` : '—'],
    ['App switches', metric(live.app_switches)],
    ['Live last seen', formatShortDateTime(live.last_seen_at)],
  ];

  return (
    <Stack spacing={1.25}>
      <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
        <Chip
          size="small"
          label={live.connected ? 'connected' : 'stale'}
          color={live.connected ? 'success' : 'default'}
          variant="outlined"
        />
        {live.presence && (
          <Chip size="small" label={live.presence} variant="outlined" />
        )}
      </Stack>
      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr' },
          gap: 1.25,
        }}
      >
        {rows.map(([label, value]) => (
          <Box key={label}>
            <Typography variant="caption" color="text.secondary">
              {label}
            </Typography>
            <Typography variant="body2" sx={{ fontFamily: label === 'Public IP' ? 'monospace' : 'inherit' }}>
              {value}
            </Typography>
          </Box>
        ))}
      </Box>
    </Stack>
  );
}

function RecentAlertsCard({
  items,
  total,
  loading,
}: {
  items: SecurityAlert[];
  total: number;
  loading: boolean;
}) {
  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 3 }}>
        <CircularProgress size={24} />
      </Box>
    );
  }

  if (items.length === 0) {
    return (
      <Typography variant="body2" color="text.secondary">
        No recent alerts for this agent.
      </Typography>
    );
  }

  return (
    <Stack spacing={0}>
      <Typography variant="caption" color="text.secondary" sx={{ mb: 1 }}>
        Showing {items.length} of {total}
      </Typography>
      <List dense disablePadding>
        {items.map((alert, index) => (
          <Box key={`${alert.id}-${alert.fingerprint || index}`}>
            {index > 0 && <Divider />}
            <ListItem
              alignItems="flex-start"
              sx={{ px: 0, py: 1.25 }}
              secondaryAction={
                <Chip
                  size="small"
                  label={alert.severity}
                  color={SEVERITY_COLOR[alert.severity] || 'default'}
                  variant="outlined"
                />
              }
            >
              <ListItemText
                primary={
                  <Typography variant="body2" sx={{ fontWeight: 600, pr: 8 }}>
                    {labelAlertType(alert.alert_type)}
                  </Typography>
                }
                secondary={
                  <Stack spacing={0.25} sx={{ mt: 0.25, pr: 8 }}>
                    <Typography variant="caption" color="text.secondary">
                      {formatShortDateTime(alert.timestamp)}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {alert.message || '—'}
                    </Typography>
                  </Stack>
                }
              />
            </ListItem>
          </Box>
        ))}
      </List>
      <Button
        component={RouterLink}
        to="/alerts"
        size="small"
        sx={{ alignSelf: 'flex-start', mt: 1 }}
      >
        Open alerts
      </Button>
    </Stack>
  );
}

function TimelineCard({ events }: { events: AgentTelemetryEvent[] }) {
  if (events.length === 0) {
    return (
      <Typography variant="body2" color="text.secondary">
        No host timeline events yet.
      </Typography>
    );
  }

  return (
    <List dense disablePadding>
      {events.map((event, index) => (
        <Box key={`${event.event_id || event.type}-${event.ts}-${index}`}>
          {index > 0 && <Divider />}
          <ListItem alignItems="flex-start" sx={{ px: 0, py: 1.25 }}>
            <ListItemText
              primary={
                <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap>
                  <Typography variant="body2" sx={{ fontWeight: 600 }}>
                    {labelEventType(event.type)}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {formatShortDateTime(event.ts)}
                  </Typography>
                </Stack>
              }
              secondary={
                <Typography variant="body2" color="text.secondary" sx={{ mt: 0.25 }}>
                  {summarizeEvent(event)}
                </Typography>
              }
            />
          </ListItem>
        </Box>
      ))}
    </List>
  );
}

const KIND_LABEL: Record<string, string> = {
  process_comm: 'Process',
  temp_path: 'Temp path',
  binary_mismatch: 'Binary mismatch',
};

function BaselineCard({
  data,
  loading,
  error,
}: {
  data: DeviceBaselineResponse;
  loading: boolean;
  error: string | null;
}) {
  const [includeSystem, setIncludeSystem] = useState(false);
  const visible = useMemo(
    () => prepareBaselineItems(data.items, { includeSystem }),
    [data.items, includeSystem]
  );
  const hiddenCount = Math.max(0, data.items.length - visible.length);

  if (loading && data.items.length === 0) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 3 }}>
        <CircularProgress size={24} />
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="warning" variant="outlined">
        Baseline unavailable. Detection-engine must be running with DETECTION_ENGINE_URL configured.
      </Alert>
    );
  }

  if (data.total === 0) {
    return (
      <Typography variant="body2" color="text.secondary">
        No learned behaviors yet for this device. Profile builds as process events are observed
        (in-memory; cleared on detection-engine restart).
      </Typography>
    );
  }

  return (
    <Stack spacing={1.5}>
      <Stack
        direction={{ xs: 'column', sm: 'row' }}
        spacing={1}
        flexWrap="wrap"
        useFlexGap
        alignItems={{ xs: 'flex-start', sm: 'center' }}
        justifyContent="space-between"
      >
        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap alignItems="center">
          <Chip
            size="small"
            label={data.profile_warm ? 'profile warm' : 'profile cold'}
            color={data.profile_warm ? 'success' : 'default'}
            variant="outlined"
          />
          <Typography variant="caption" color="text.secondary">
            Showing {visible.length} of {data.total} · sorted by frequency
            {!includeSystem && hiddenCount > 0 ? ` · ${hiddenCount} system hidden` : ''}
          </Typography>
        </Stack>
        <FormControlLabel
          control={
            <Switch
              size="small"
              checked={includeSystem}
              onChange={(_e, checked) => setIncludeSystem(checked)}
            />
          }
          label={<Typography variant="caption">Show system processes</Typography>}
        />
      </Stack>
      {visible.length === 0 ? (
        <Typography variant="body2" color="text.secondary">
          No application-like processes yet. Quit/reopen apps (Chrome, Terminal) or enable “Show
          system processes”.
        </Typography>
      ) : (
        <List dense disablePadding>
          {visible.map((item: DeviceBaselineItem, index: number) => (
            <Box key={`${item.behavior_kind}:${item.behavior_key}`}>
              {index > 0 && <Divider />}
              <ListItem
                alignItems="flex-start"
                sx={{ px: 0, py: 1.25 }}
                secondaryAction={
                  <Chip
                    size="small"
                    label={item.established ? 'established' : 'learning'}
                    color={item.established ? 'success' : 'default'}
                    variant="outlined"
                  />
                }
              >
                <ListItemText
                  primary={
                    <Typography
                      variant="body2"
                      sx={{ fontWeight: 600, pr: 10, fontFamily: 'monospace' }}
                    >
                      {displayBaselineKey(item.behavior_key)}
                    </Typography>
                  }
                  secondary={
                    <Stack spacing={0.25} sx={{ mt: 0.25, pr: 10 }}>
                      <Typography variant="caption" color="text.secondary">
                        {KIND_LABEL[item.behavior_kind] || item.behavior_kind}
                        {displayBaselineKey(item.behavior_key) !== item.behavior_key
                          ? ` · ${item.behavior_key}`
                          : ''}{' '}
                        · seen {item.count}× · last {formatShortDateTime(item.last_seen_at)}
                      </Typography>
                    </Stack>
                  }
                />
              </ListItem>
            </Box>
          ))}
        </List>
      )}
    </Stack>
  );
}

export default function AgentDetail({ agentId }: { agentId: string }) {
  const { agent, live, events, loading, error, liveMissing, refresh, refreshEvents } =
    useAgentDetail(agentId);
  const {
    items: alerts,
    total: alertTotal,
    loading: alertsLoading,
    refetch: refetchAlerts,
  } = useSecurityAlerts({ deviceId: agentId, pageSize: 15 });
  const {
    data: baseline,
    loading: baselineLoading,
    error: baselineError,
    refetch: refetchBaseline,
  } = useDeviceBaseline(agentId);

  const online = isAgentOnline(agent?.last_seen_at);

  const onRefresh = () => {
    refresh();
    refetchAlerts();
    refetchBaseline();
  };

  if (loading && !agent) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error || !agent) {
    return (
      <Box sx={{ width: '100%', maxWidth: { sm: '100%', md: '1700px' } }}>
        <Button
          component={RouterLink}
          to="/agents"
          startIcon={<ArrowBackIcon />}
          size="small"
          sx={{ mb: 2 }}
        >
          Back to agents
        </Button>
        <Alert severity="error">{error || 'Agent not found'}</Alert>
      </Box>
    );
  }

  const osLine = [agent.os, agent.os_version, agent.arch].filter(Boolean).join(' · ') || '—';

  return (
    <Box sx={{ width: '100%', maxWidth: { sm: '100%', md: '1700px' } }}>
      <Stack
        direction={{ xs: 'column', sm: 'row' }}
        justifyContent="space-between"
        alignItems={{ xs: 'stretch', sm: 'flex-start' }}
        spacing={1.5}
        sx={{ mb: 2 }}
      >
        <Box>
          <Button
            component={RouterLink}
            to="/agents"
            startIcon={<ArrowBackIcon />}
            size="small"
            sx={{ mb: 1 }}
          >
            Back to agents
          </Button>
          <Typography component="h1" variant="h5" sx={{ mb: 0.5 }}>
            {agent.hostname || agent.agent_id}
          </Typography>
          <Typography
            variant="body2"
            color="text.secondary"
            sx={{ fontFamily: 'monospace', wordBreak: 'break-all' }}
          >
            {agent.agent_id}
          </Typography>
          <Stack direction="row" spacing={1} sx={{ mt: 1.25 }} flexWrap="wrap" useFlexGap>
            <Chip
              size="small"
              label={online ? 'online' : 'offline'}
              color={online ? 'success' : 'default'}
              variant="outlined"
            />
            <Chip size="small" label={agent.status || 'registered'} variant="outlined" />
            {live?.connected && (
              <Chip size="small" label="live twin" color="success" variant="outlined" />
            )}
          </Stack>
        </Box>
        <Tooltip title="Refresh">
          <IconButton onClick={onRefresh} disabled={loading || alertsLoading || baselineLoading}>
            <RefreshIcon />
          </IconButton>
        </Tooltip>
      </Stack>

      <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
        <Box
          sx={{
            display: 'grid',
            gridTemplateColumns: { xs: '1fr', md: 'repeat(4, 1fr)' },
            gap: 2,
          }}
        >
          <Box>
            <Typography variant="caption" color="text.secondary">
              OS
            </Typography>
            <Typography variant="body2">{osLine}</Typography>
          </Box>
          <Box>
            <Typography variant="caption" color="text.secondary">
              Agent version
            </Typography>
            <Typography variant="body2">{agent.agent_version || '—'}</Typography>
          </Box>
          <Box>
            <Typography variant="caption" color="text.secondary">
              First seen
            </Typography>
            <Typography variant="body2">{formatShortDateTime(agent.first_seen_at)}</Typography>
          </Box>
          <Box>
            <Typography variant="caption" color="text.secondary">
              Last seen
            </Typography>
            <Typography variant="body2">{formatShortDateTime(agent.last_seen_at)}</Typography>
          </Box>
        </Box>
      </Paper>

      <Grid container spacing={2} sx={{ mb: 2 }}>
        <Grid size={{ xs: 12, md: 6 }}>
          <Paper variant="outlined" sx={{ p: 2, height: '100%' }}>
            <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 1.5 }}>
              Last telemetry
            </Typography>
            <TelemetryCard live={live} liveMissing={liveMissing} />
          </Paper>
        </Grid>
        <Grid size={{ xs: 12, md: 6 }}>
          <Paper variant="outlined" sx={{ p: 2, height: '100%' }}>
            <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 1.5 }}>
              Recent alerts
            </Typography>
            <RecentAlertsCard items={alerts} total={alertTotal} loading={alertsLoading} />
          </Paper>
        </Grid>
      </Grid>

      <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
        <Stack
          direction="row"
          justifyContent="space-between"
          alignItems="center"
          spacing={1}
          sx={{ mb: 1.5 }}
        >
          <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
            Behavioral baseline
          </Typography>
          <Tooltip title="Refresh baseline">
            <span>
              <IconButton
                size="small"
                onClick={() => refetchBaseline()}
                disabled={baselineLoading}
                aria-label="Refresh behavioral baseline"
              >
                <RefreshIcon fontSize="small" />
              </IconButton>
            </span>
          </Tooltip>
        </Stack>
        <BaselineCard data={baseline} loading={baselineLoading} error={baselineError} />
      </Paper>

      <Paper variant="outlined" sx={{ p: 2 }}>
        <Stack
          direction="row"
          justifyContent="space-between"
          alignItems="center"
          spacing={1}
          sx={{ mb: 1.5 }}
        >
          <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
            Host timeline
          </Typography>
          <Tooltip title="Refresh timeline">
            <span>
              <IconButton
                size="small"
                onClick={() => refreshEvents()}
                disabled={loading}
                aria-label="Refresh host timeline"
              >
                <RefreshIcon fontSize="small" />
              </IconButton>
            </span>
          </Tooltip>
        </Stack>
        <TimelineCard events={events} />
      </Paper>
    </Box>
  );
}
