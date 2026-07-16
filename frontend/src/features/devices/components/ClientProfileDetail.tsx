import { useCallback, useEffect, useState } from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Paper from '@mui/material/Paper';
import Stack from '@mui/material/Stack';
import Chip from '@mui/material/Chip';
import CircularProgress from '@mui/material/CircularProgress';
import Alert from '@mui/material/Alert';
import Button from '@mui/material/Button';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemText from '@mui/material/ListItemText';
import Divider from '@mui/material/Divider';
import Tooltip from '@mui/material/Tooltip';
import RefreshIcon from '@mui/icons-material/Refresh';
import AutoAwesomeOutlinedIcon from '@mui/icons-material/AutoAwesomeOutlined';
import HelpOutlineIcon from '@mui/icons-material/HelpOutline';
import IconButton from '@mui/material/IconButton';
import { devicesApi } from '../config/api';
import {
  BehaviorProfile,
  BehaviorReview,
  Device,
  DeviceCountrySummary,
  DeviceLoginGeoSummary,
} from '../types/device';
import { BehaviorAlert } from '../types/behaviorAlert';
import BaselineSummary from './BaselineSummary';
import DeviceCountriesSection from './DeviceCountriesSection';
import NetworkAttributionSection from './NetworkAttributionSection';
import DeviceLoginLocationSection from './DeviceLoginLocationSection';
import { countryLabel } from '../utils/countryDisplay';
import { formatShortDateTime } from '../../../shared/utils/dateUtils';
import { chromelessIconButtonSx } from '../../../shared/theme/chromelessIconButtonSx';

interface ClientProfileDetailProps {
  device: Device;
  countrySummary?: DeviceCountrySummary | null;
  loginGeoSummary?: DeviceLoginGeoSummary | null;
}

export default function ClientProfileDetail({
  device,
  countrySummary,
  loginGeoSummary,
}: ClientProfileDetailProps) {
  const [profile, setProfile] = useState<BehaviorProfile | null>(null);
  const [events, setEvents] = useState<BehaviorAlert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [review, setReview] = useState<BehaviorReview | null>(null);
  const [reviewLoading, setReviewLoading] = useState(false);
  const [reviewError, setReviewError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [p, ev] = await Promise.all([
        devicesApi.getBehaviorProfile(device.id),
        devicesApi.getBehaviorEvents(device.id, 1, 10),
      ]);
      setProfile(p);
      setEvents(ev.items);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load profile');
    } finally {
      setLoading(false);
    }
  }, [device.id]);

  useEffect(() => {
    load();
  }, [load]);

  const loadReview = useCallback(
    async (refresh = false) => {
      setReviewLoading(true);
      setReviewError(null);
      try {
        const r = await devicesApi.getBehaviorReview(device.id, refresh);
        setReview(r);
      } catch (e) {
        setReviewError(e instanceof Error ? e.message : 'Failed to load behavior explanation');
      } finally {
        setReviewLoading(false);
      }
    },
    [device.id],
  );

  useEffect(() => {
    if (!loading && profile?.profile_ready) {
      loadReview();
    }
  }, [loading, profile?.profile_ready, loadReview]);

  const label = device.hostname || device.external_id;

  return (
    <Paper variant="outlined" sx={{ p: 3, minHeight: 400 }}>
      <Stack spacing={3}>
        <Stack direction="row" justifyContent="space-between" alignItems="flex-start" flexWrap="wrap" gap={2}>
          <Box>
            <Typography variant="h5">{label}</Typography>
            <Typography variant="body2" color="text.secondary">
              {device.external_id}
              {device.mac_address ? ` · ${device.mac_address}` : ''}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Source: {device.source}
            </Typography>
            {loginGeoSummary?.country_code && (
              <Typography variant="caption" color="text.secondary" display="block">
                Last login from:{' '}
                {countryLabel(loginGeoSummary.country_code, loginGeoSummary.country_name)}
              </Typography>
            )}
            {countrySummary?.primary_country_code && (
              <Typography variant="caption" color="text.secondary" display="block">
                Primary DNS region:{' '}
                {countryLabel(
                  countrySummary.primary_country_code,
                  countrySummary.primary_country_name,
                )}
              </Typography>
            )}
          </Box>
          <Stack direction="row" spacing={1} alignItems="center">
            <Stack direction="row" alignItems="center" spacing={0.25}>
              <Chip
                label={profile?.profile_ready ? 'Baseline ready' : 'Learning'}
                color={profile?.profile_ready ? 'success' : 'default'}
                variant="outlined"
              />
              <Tooltip
                title={
                  profile?.profile_ready
                    ? 'Enough DNS history exists. “Normal” stats refresh about every hour; recent activity is scored against them.'
                    : 'Collecting DNS history to learn this device’s normal patterns before anomaly scoring runs.'
                }
                arrow
              >
                <IconButton size="small" aria-label="About baseline status" sx={{ p: 0.25, ...chromelessIconButtonSx }}>
                  <HelpOutlineIcon sx={{ fontSize: 16 }} />
                </IconButton>
              </Tooltip>
            </Stack>
            {profile?.last_score != null && (
              <Stack direction="row" alignItems="center" spacing={0.25}>
                <Chip label={`Score: ${profile.last_score}`} color="warning" variant="outlined" />
                <Tooltip
                  title="0–100 unusual-activity score for the last ~15 minutes vs this baseline."
                  arrow
                >
                  <IconButton size="small" aria-label="About behavior score" sx={{ p: 0.25, ...chromelessIconButtonSx }}>
                    <HelpOutlineIcon sx={{ fontSize: 16 }} />
                  </IconButton>
                </Tooltip>
              </Stack>
            )}
            <Button size="small" onClick={load}>
              Refresh
            </Button>
          </Stack>
        </Stack>

        {loading && (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
            <CircularProgress />
          </Box>
        )}
        {error && <Alert severity="error">{error}</Alert>}

        {!loading && profile && (
          <>
            <Box>
              <Stack direction="row" alignItems="center" spacing={0.5} sx={{ mb: 1.5 }}>
                <Typography variant="subtitle1">Behavior baseline</Typography>
                <Tooltip
                  title="Learned “normal” DNS habits for this device. Stats update from recent history while the device is active."
                  arrow
                >
                  <IconButton size="small" aria-label="About behavior baseline" sx={{ p: 0.25, ...chromelessIconButtonSx }}>
                    <HelpOutlineIcon sx={{ fontSize: 18 }} />
                  </IconButton>
                </Tooltip>
              </Stack>
              {profile.profile_ready && Object.keys(profile.baseline).length > 0 ? (
                <BaselineSummary baseline={profile.baseline} />
              ) : (
                <Alert severity="info" variant="outlined">
                  Profile is still learning. TrustEdge needs more DNS history before a baseline is
                  computed.
                </Alert>
              )}
              {profile.last_scored_at && (
                <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                  Last scored: {formatShortDateTime(profile.last_scored_at)}
                </Typography>
              )}
            </Box>

            <NetworkAttributionSection deviceId={device.id} />

            <DeviceLoginLocationSection deviceId={device.id} />

            <DeviceCountriesSection deviceId={device.id} />

            <Box>
              <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 1 }}>
                <AutoAwesomeOutlinedIcon color="primary" fontSize="small" />
                <Typography variant="subtitle1" sx={{ flex: 1 }}>
                  What this means
                </Typography>
                {review?.source === 'llm' && review.llm_model && (
                  <Chip size="small" label={review.llm_model} variant="outlined" color="primary" />
                )}
                <Tooltip title="Regenerate explanation">
                  <span>
                    <Button
                      size="small"
                      startIcon={
                        reviewLoading ? <CircularProgress size={14} /> : <RefreshIcon fontSize="small" />
                      }
                      onClick={() => loadReview(true)}
                      disabled={reviewLoading}
                    >
                      Refresh
                    </Button>
                  </span>
                </Tooltip>
              </Stack>
              {reviewLoading && !review && (
                <Typography variant="body2" color="text.secondary">
                  Generating explanation…
                </Typography>
              )}
              {reviewError && (
                <Alert severity="warning" sx={{ mb: 1 }}>
                  {reviewError}
                </Alert>
              )}
              {review?.summary && (
                <Typography variant="body2" sx={{ lineHeight: 1.65 }}>
                  {review.summary}
                </Typography>
              )}
            </Box>

            <Box>
              <Typography variant="subtitle1" sx={{ mb: 1 }}>
                Recent behavior alerts
              </Typography>
              {events.length === 0 ? (
                <Typography variant="body2" color="text.secondary">
                  No behavior anomalies recorded for this device.
                </Typography>
              ) : (
                <List dense disablePadding>
                  {events.map((ev) => (
                    <Box key={ev.id}>
                      <ListItem alignItems="flex-start">
                        <ListItemText
                          primary={ev.domain || ev.root_domain || '—'}
                          secondary={
                            <>
                              {formatShortDateTime(ev.timestamp)}
                              <br />
                              {ev.parent_summary || ev.message || '—'}
                            </>
                          }
                        />
                      </ListItem>
                      <Divider />
                    </Box>
                  ))}
                </List>
              )}
            </Box>
          </>
        )}
      </Stack>
    </Paper>
  );
}
