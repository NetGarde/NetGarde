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
import RefreshIcon from '@mui/icons-material/Refresh';
import SecurityIcon from '@mui/icons-material/Security';
import { useTwinAlerts } from '../../twin/hooks/useTwinAlerts';
import { TwinAlert } from '../../twin/types/twinAlert';
import { formatShortDateTime } from '../../../shared/utils/dateUtils';

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
};

function AttackAlertRow({ alert }: { alert: TwinAlert }) {
  const label = TYPE_LABEL[alert.alert_type] || alert.alert_type;
  const severity = SEVERITY_COLOR[alert.severity] || 'default';

  return (
    <ListItem sx={{ py: 0.75, px: 1.5 }}>
      <ListItemText
        primary={
          <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
            <Chip label={label} size="small" color={severity} variant="outlined" />
            <Chip label={alert.severity} size="small" color={severity} />
            <Typography variant="body2" sx={{ fontWeight: 600, flex: 1 }}>
              {alert.message || label}
            </Typography>
          </Stack>
        }
        secondary={
          <Stack direction="row" spacing={1.5} alignItems="center" flexWrap="wrap" sx={{ mt: 0.5 }}>
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

export default function AttackAlertsView() {
  const { items, total, loading, refetch } = useTwinAlerts({ severity: 'high' });

  return (
    <Paper
      variant="outlined"
      sx={{
        height: '100%',
        minHeight: 280,
        maxHeight: 420,
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ px: 2, py: 1.5 }}>
        <Stack direction="row" spacing={1} alignItems="center">
          <SecurityIcon color="error" fontSize="small" />
          <Typography variant="subtitle2">Attack alerts</Typography>
          {total > 0 && <Chip label={total} size="small" color="error" variant="outlined" />}
        </Stack>
        <Tooltip title="Refresh">
          <IconButton size="small" onClick={refetch} disabled={loading}>
            <RefreshIcon fontSize="small" />
          </IconButton>
        </Tooltip>
      </Stack>
      <Divider />
      <Box sx={{ flex: 1, minHeight: 0, overflowY: 'auto', overflowX: 'hidden' }}>
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
            <CircularProgress size={28} />
          </Box>
        ) : items.length === 0 ? (
          <Typography color="text.secondary" sx={{ p: 2 }}>
            No high-severity attack alerts yet. Temp-path execution and related process rules appear
            here.
          </Typography>
        ) : (
          <List dense disablePadding>
            {items.map((alert, index) => (
              <Box key={alert.id}>
                <AttackAlertRow alert={alert} />
                {index < items.length - 1 && <Divider component="li" />}
              </Box>
            ))}
          </List>
        )}
      </Box>
    </Paper>
  );
}
