import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Chip from '@mui/material/Chip';
import Stack from '@mui/material/Stack';
import Paper from '@mui/material/Paper';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemText from '@mui/material/ListItemText';
import Divider from '@mui/material/Divider';
import IconButton from '@mui/material/IconButton';
import Tooltip from '@mui/material/Tooltip';
import CircularProgress from '@mui/material/CircularProgress';
import ToggleButton from '@mui/material/ToggleButton';
import ToggleButtonGroup from '@mui/material/ToggleButtonGroup';
import RefreshIcon from '@mui/icons-material/Refresh';
import { useMemo, useState } from 'react';
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
};

type SeverityFilter = 'all' | 'high' | 'medium' | 'low';

function AlertRow({ alert }: { alert: SecurityAlert }) {
  const label = TYPE_LABEL[alert.alert_type] || alert.alert_type.replace(/_/g, ' ');
  const severity = SEVERITY_COLOR[alert.severity] || 'default';

  return (
    <ListItem sx={{ py: 1, px: 2 }}>
      <ListItemText
        primary={
          <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap>
            <Chip label={label} size="small" color={severity} variant="outlined" />
            <Chip label={alert.severity} size="small" color={severity} />
            <Typography variant="body2" sx={{ fontWeight: 600, flex: 1, minWidth: 160 }}>
              {alert.message || label}
            </Typography>
          </Stack>
        }
        secondary={
          <Stack direction="row" spacing={1.5} alignItems="center" flexWrap="wrap" useFlexGap sx={{ mt: 0.5 }}>
            <Typography variant="caption" color="text.secondary">
              {formatShortDateTime(alert.timestamp)}
            </Typography>
            <Typography variant="caption" color="text.secondary" sx={{ fontFamily: 'monospace' }}>
              {alert.device_id}
            </Typography>
            {alert.event_type && (
              <Typography variant="caption" color="text.secondary">
                {alert.event_type}
              </Typography>
            )}
          </Stack>
        }
      />
    </ListItem>
  );
}

export default function AlertsPage() {
  const [severityFilter, setSeverityFilter] = useState<SeverityFilter>('all');
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
            Detection findings from the rules engine.
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
                <AlertRow alert={alert} />
                {index < items.length - 1 && <Divider component="li" />}
              </Box>
            ))}
          </List>
        )}
      </Paper>
    </Box>
  );
}
