import { useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Paper from '@mui/material/Paper';
import Stack from '@mui/material/Stack';
import Button from '@mui/material/Button';
import Chip from '@mui/material/Chip';
import Alert from '@mui/material/Alert';
import CircularProgress from '@mui/material/CircularProgress';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Link from '@mui/material/Link';
import RefreshIcon from '@mui/icons-material/Refresh';
import BlockIcon from '@mui/icons-material/Block';
import { useBlockedClients } from './hooks/useBlockedClients';
import { devicesApi } from './config/api';
import { BlockedClientSummary } from './types/device';
import { clientProfilePath } from './clientProfilePaths';
import { formatShortDateTime } from '../../shared/utils/dateUtils';

function clientLabel(item: BlockedClientSummary): string {
  return item.hostname || item.client_ip || `Device #${item.device_id}`;
}

function formatBlockSource(source: string | null): string {
  if (!source) return '—';
  if (source === 'admin_manual') return 'Admin';
  if (source === 'behavior_auto') return 'Behavior auto';
  if (source === 'forbidden_country') return 'Forbidden country';
  return source;
}

function statusChips(item: BlockedClientSummary) {
  const chips = [];
  if (item.in_quarantine) {
    chips.push(
      <Chip key="quarantine" label="Full network block" size="small" color="error" />,
    );
  }
  if (item.active_block_count > 0) {
    chips.push(
      <Chip
        key="domains"
        label={`${item.active_block_count} domain block${item.active_block_count === 1 ? '' : 's'}`}
        size="small"
        color="warning"
        variant="outlined"
      />,
    );
  }
  return chips;
}

export default function BlockedClients() {
  const { items, total, loading, error, refresh } = useBlockedClients();
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [unblockingId, setUnblockingId] = useState<number | null>(null);

  const unblockClient = async (deviceId: number) => {
    setUnblockingId(deviceId);
    setActionError(null);
    setActionMessage(null);
    try {
      const result = await devicesApi.endQuarantine(deviceId);
      setActionMessage(result.message || 'Client unblocked.');
      await refresh();
    } catch (e) {
      setActionError(e instanceof Error ? e.message : 'Failed to unblock client');
    } finally {
      setUnblockingId(null);
    }
  };

  return (
    <Box sx={{ width: '100%', maxWidth: { sm: '100%', md: '1700px' } }}>
      <Stack
        direction={{ xs: 'column', sm: 'row' }}
        justifyContent="space-between"
        alignItems={{ xs: 'stretch', sm: 'flex-start' }}
        spacing={1}
        sx={{ mb: 3 }}
      >
        <Box>
          <Typography component="h1" variant="h5" sx={{ mb: 0.5 }}>
            Blocked clients
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Clients under full network block or active per-device domain blocks.
          </Typography>
        </Box>
        <Button
          size="small"
          variant="outlined"
          startIcon={<RefreshIcon />}
          onClick={refresh}
          disabled={loading}
          sx={{ flexShrink: 0, alignSelf: { sm: 'flex-start' } }}
        >
          Refresh
        </Button>
      </Stack>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}
      {actionError && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setActionError(null)}>
          {actionError}
        </Alert>
      )}
      {actionMessage && (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setActionMessage(null)}>
          {actionMessage}
        </Alert>
      )}

      <Paper variant="outlined">
        {loading && items.length === 0 ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
            <CircularProgress />
          </Box>
        ) : items.length === 0 ? (
          <Stack alignItems="center" spacing={1} sx={{ py: 8, px: 2 }}>
            <BlockIcon color="disabled" sx={{ fontSize: 40 }} />
            <Typography variant="body1" color="text.secondary">
              No blocked clients right now.
            </Typography>
            <Typography variant="body2" color="text.secondary" textAlign="center">
              Full blocks and behavior-driven domain blocks appear here automatically.
            </Typography>
          </Stack>
        ) : (
          <>
            <Box sx={{ px: 2, py: 1.5, borderBottom: 1, borderColor: 'divider' }}>
              <Typography variant="subtitle2" color="text.secondary">
                {total} blocked client{total === 1 ? '' : 's'}
              </Typography>
            </Box>
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Client</TableCell>
                    <TableCell>Client IP</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Expires / latest</TableCell>
                    <TableCell>Score</TableCell>
                    <TableCell align="right">Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {items.map((item) => (
                    <TableRow key={item.device_id} hover>
                      <TableCell>
                        <Link
                          component={RouterLink}
                          to={clientProfilePath(item.device_id)}
                          underline="hover"
                          sx={{ fontWeight: 600 }}
                        >
                          {clientLabel(item)}
                        </Link>
                        {item.mac_address && (
                          <Typography variant="caption" color="text.secondary" display="block">
                            {item.mac_address}
                          </Typography>
                        )}
                      </TableCell>
                      <TableCell sx={{ fontFamily: 'monospace' }}>
                        {item.client_ip || '—'}
                      </TableCell>
                      <TableCell>
                        <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap>
                          {statusChips(item)}
                        </Stack>
                        {item.latest_blocked_domain && (
                          <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 0.5 }}>
                            Latest: {item.latest_blocked_domain} ({formatBlockSource(item.latest_block_source)})
                          </Typography>
                        )}
                      </TableCell>
                      <TableCell>
                        {item.in_quarantine && item.quarantine_expires_at ? (
                          <Typography variant="body2">
                            {formatShortDateTime(item.quarantine_expires_at)}
                          </Typography>
                        ) : item.latest_block_at ? (
                          <Typography variant="body2">
                            {formatShortDateTime(item.latest_block_at)}
                          </Typography>
                        ) : (
                          '—'
                        )}
                      </TableCell>
                      <TableCell>
                        {item.last_score != null ? (
                          <Chip label={item.last_score} size="small" variant="outlined" />
                        ) : (
                          '—'
                        )}
                      </TableCell>
                      <TableCell align="right">
                        <Stack direction="row" spacing={1} justifyContent="flex-end">
                          <Button
                            component={RouterLink}
                            to={clientProfilePath(item.device_id)}
                            size="small"
                          >
                            Profile
                          </Button>
                          {item.in_quarantine && (
                            <Button
                              size="small"
                              color="success"
                              variant="contained"
                              disabled={unblockingId === item.device_id}
                              onClick={() => unblockClient(item.device_id)}
                            >
                              {unblockingId === item.device_id ? 'Unblocking…' : 'Unblock'}
                            </Button>
                          )}
                        </Stack>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </>
        )}
      </Paper>
    </Box>
  );
}
