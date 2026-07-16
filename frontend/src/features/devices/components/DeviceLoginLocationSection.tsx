import { useCallback, useEffect, useState } from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Stack from '@mui/material/Stack';
import Chip from '@mui/material/Chip';
import CircularProgress from '@mui/material/CircularProgress';
import Alert from '@mui/material/Alert';
import Tooltip from '@mui/material/Tooltip';
import HelpOutlineIcon from '@mui/icons-material/HelpOutline';
import LocationOnIcon from '@mui/icons-material/LocationOn';
import { devicesApi } from '../config/api';
import { DeviceLoginGeo } from '../types/device';
import { countryFlagEmoji, countryLabel } from '../utils/countryDisplay';
import { formatShortDateTime } from '../../../shared/utils/dateUtils';

interface DeviceLoginLocationSectionProps {
  deviceId: number;
}

export default function DeviceLoginLocationSection({ deviceId }: DeviceLoginLocationSectionProps) {
  const [data, setData] = useState<DeviceLoginGeo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const geo = await devicesApi.getLoginLocation(deviceId);
      setData(geo);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load login location');
    } finally {
      setLoading(false);
    }
  }, [deviceId]);

  useEffect(() => {
    load();
  }, [load]);

  const latest = data?.latest;

  return (
    <Box>
      <Stack direction="row" alignItems="center" spacing={0.5} sx={{ mb: 1 }}>
        <LocationOnIcon color="primary" fontSize="small" />
        <Typography variant="subtitle1" sx={{ flex: 1 }}>
          Login location
        </Typography>
        <Tooltip
          title="Estimated from the device's public IP at check-in. This is physical location, not DNS domain country."
          arrow
        >
          <Box
            component="span"
            aria-label="About login location"
            sx={{
              display: 'inline-flex',
              alignItems: 'center',
              cursor: 'help',
              color: 'text.secondary',
              '&:hover': { color: 'text.primary' },
            }}
          >
            <HelpOutlineIcon sx={{ fontSize: 18 }} />
          </Box>
        </Tooltip>
      </Stack>

      {loading && (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <CircularProgress size={20} />
          <Typography variant="body2" color="text.secondary">
            Loading…
          </Typography>
        </Box>
      )}
      {error && (
        <Alert severity="warning" sx={{ mb: 1 }}>
          {error}
        </Alert>
      )}
      {!loading && !latest && !error && (
        <Typography variant="body2" color="text.secondary">
          No login location recorded yet. Location appears after the next agent check-in with a public IP.
        </Typography>
      )}
      {!loading && latest && (
        <Stack spacing={1}>
          {latest.country_code ? (
            <Chip
              size="small"
              label={countryLabel(latest.country_code, latest.country_name)}
              icon={<span>{countryFlagEmoji(latest.country_code)}</span>}
              variant="outlined"
            />
          ) : (
            <Typography variant="body2" color="text.secondary">
              Country unknown (IP {latest.public_ip})
            </Typography>
          )}
          <Typography variant="body2" color="text.secondary">
            {[
              latest.city,
              latest.region_name,
              latest.country_name,
            ]
              .filter(Boolean)
              .join(', ') || `Public IP ${latest.public_ip}`}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            Last seen at login · {formatShortDateTime(latest.observed_at)}
          </Typography>
          {data && data.history.length > 1 && (
            <Typography variant="caption" color="text.secondary">
              {data.history.length} recent login(s) on record
            </Typography>
          )}
        </Stack>
      )}
    </Box>
  );
}
