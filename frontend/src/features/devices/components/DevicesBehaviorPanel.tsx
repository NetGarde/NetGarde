import { useCallback, useEffect, useState } from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Paper from '@mui/material/Paper';
import Stack from '@mui/material/Stack';
import Chip from '@mui/material/Chip';
import Switch from '@mui/material/Switch';
import FormControlLabel from '@mui/material/FormControlLabel';
import CircularProgress from '@mui/material/CircularProgress';
import Alert from '@mui/material/Alert';
import Button from '@mui/material/Button';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemText from '@mui/material/ListItemText';
import Divider from '@mui/material/Divider';
import { useDevices } from '../hooks/useDevices';
import { devicesApi } from '../config/api';
import {
  BehaviorProfile,
  ClientBlockedDomain,
  Device,
  DeviceSecurityPolicy,
} from '../types/device';
import { formatShortDateTime } from '../../../shared/utils/dateUtils';

function DeviceBehaviorCard({ device }: { device: Device }) {
  const [profile, setProfile] = useState<BehaviorProfile | null>(null);
  const [policy, setPolicy] = useState<DeviceSecurityPolicy | null>(null);
  const [blocks, setBlocks] = useState<ClientBlockedDomain[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [p, pol, b] = await Promise.all([
        devicesApi.getBehaviorProfile(device.id),
        devicesApi.getSecurityPolicy(device.id),
        devicesApi.listClientBlocks(device.id),
      ]);
      setProfile(p);
      setPolicy(pol);
      setBlocks(b);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load device behavior');
    } finally {
      setLoading(false);
    }
  }, [device.id]);

  useEffect(() => {
    load();
  }, [load]);

  const toggleAutoBlock = async () => {
    if (!policy) return;
    setSaving(true);
    try {
      const updated = await devicesApi.updateSecurityPolicy(device.id, {
        auto_block_enabled: !policy.auto_block_enabled,
      });
      setPolicy(updated);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to update policy');
    } finally {
      setSaving(false);
    }
  };

  const revokeBlock = async (blockId: number) => {
    try {
      await devicesApi.revokeClientBlock(device.id, blockId);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to revoke block');
    }
  };

  const label = device.hostname || device.external_id;
  const profileStatus = profile?.profile_ready ? 'Ready' : 'Learning';

  return (
    <Paper variant="outlined" sx={{ p: 2 }}>
      <Stack spacing={1.5}>
        <Stack direction="row" justifyContent="space-between" alignItems="center" flexWrap="wrap" gap={1}>
          <Box>
            <Typography variant="subtitle1">{label}</Typography>
            <Typography variant="caption" color="text.secondary">
              {device.external_id}
              {device.mac_address ? ` · ${device.mac_address}` : ''}
            </Typography>
          </Box>
          <Stack direction="row" spacing={1} alignItems="center">
            <Chip
              size="small"
              label={profileStatus}
              color={profile?.profile_ready ? 'success' : 'default'}
              variant="outlined"
            />
            {profile?.last_score != null && (
              <Chip size="small" label={`Score: ${profile.last_score}`} variant="outlined" />
            )}
          </Stack>
        </Stack>

        {loading && <CircularProgress size={24} />}
        {error && <Alert severity="error">{error}</Alert>}

        {!loading && policy && (
          <FormControlLabel
            control={
              <Switch
                checked={policy.auto_block_enabled}
                onChange={toggleAutoBlock}
                disabled={saving}
              />
            }
            label="Auto-block on abnormal behavior"
          />
        )}

        {!loading && profile && !profile.profile_ready && (
          <Typography variant="body2" color="text.secondary">
            Baseline is still learning and needs more DNS history. (This threshold is configurable
            by the server.)
          </Typography>
        )}

        {blocks.length > 0 && (
          <Box>
            <Typography variant="subtitle2" sx={{ mb: 1 }}>
              Active per-device blocks
            </Typography>
            <List dense disablePadding>
              {blocks.map((b) => (
                <Box key={b.id}>
                  <ListItem
                    secondaryAction={
                      <Button size="small" onClick={() => revokeBlock(b.id)}>
                        Revoke
                      </Button>
                    }
                  >
                    <ListItemText
                      primary={b.domain}
                      secondary={
                        b.expires_at
                          ? `Expires ${formatShortDateTime(b.expires_at)} · score ${b.score ?? '—'}`
                          : `score ${b.score ?? '—'}`
                      }
                    />
                  </ListItem>
                  <Divider />
                </Box>
              ))}
            </List>
          </Box>
        )}
      </Stack>
    </Paper>
  );
}

export default function DevicesBehaviorPanel() {
  const { devices, loading, error, refresh } = useDevices();

  return (
    <Box>
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
        <Typography component="h2" variant="h6">
          Device behavior
        </Typography>
        <Button size="small" onClick={refresh}>
          Refresh
        </Button>
      </Stack>
      {loading && <CircularProgress />}
      {error && <Alert severity="error">{error}</Alert>}
      {!loading && devices.length === 0 && (
        <Typography variant="body2" color="text.secondary">
          No devices yet. DHCP sync or DNS traffic will register clients.
        </Typography>
      )}
      <Stack spacing={2}>
        {devices.map((d) => (
          <DeviceBehaviorCard key={d.id} device={d} />
        ))}
      </Stack>
    </Box>
  );
}
