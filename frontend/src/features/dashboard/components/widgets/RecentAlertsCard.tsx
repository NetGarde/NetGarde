import { Link as RouterLink } from 'react-router-dom';
import Box from '@mui/material/Box';
import Chip from '@mui/material/Chip';
import CircularProgress from '@mui/material/CircularProgress';
import Link from '@mui/material/Link';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import DashboardCard from './DashboardCard';
import { useSecurityAlerts } from '../../../twin/hooks/useSecurityAlerts';
import { formatShortDateTime } from '../../../../shared/utils/dateUtils';

const SEVERITY_COLOR: Record<string, 'error' | 'warning' | 'info' | 'default'> = {
  high: 'error',
  medium: 'warning',
  low: 'info',
};

export default function RecentAlertsCard() {
  const { items, loading } = useSecurityAlerts({ pageSize: 6 });

  return (
    <DashboardCard
      title="Recent alerts"
      action={
        <Link component={RouterLink} to="/alerts" variant="caption" underline="hover" color="text.secondary">
          Show all
        </Link>
      }
    >
      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
          <CircularProgress size={24} />
        </Box>
      ) : items.length === 0 ? (
        <Typography variant="body2" color="text.secondary" sx={{ py: 4, textAlign: 'center' }}>
          No alerts in the current window.
        </Typography>
      ) : (
        <Stack spacing={0} divider={<Box sx={{ borderBottom: '1px solid', borderColor: 'divider' }} />}>
          {items.map((alert) => (
            <Stack
              key={alert.id}
              direction="row"
              alignItems="flex-start"
              justifyContent="space-between"
              spacing={1}
              sx={{ py: 1.25 }}
            >
              <Box sx={{ minWidth: 0, flex: 1 }}>
                <Typography variant="body2" sx={{ fontWeight: 500 }} noWrap>
                  {alert.message || alert.alert_type.replace(/_/g, ' ')}
                </Typography>
                <Typography variant="caption" color="text.secondary" noWrap>
                  {alert.device_id} · {formatShortDateTime(alert.timestamp)}
                </Typography>
              </Box>
              <Chip
                size="small"
                label={alert.severity}
                color={SEVERITY_COLOR[alert.severity] ?? 'default'}
                variant="outlined"
                sx={{ textTransform: 'capitalize', height: 22, fontSize: '0.7rem' }}
              />
            </Stack>
          ))}
        </Stack>
      )}
    </DashboardCard>
  );
}
