import { useEffect, useMemo, useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import Box from '@mui/material/Box';
import Chip from '@mui/material/Chip';
import CircularProgress from '@mui/material/CircularProgress';
import Divider from '@mui/material/Divider';
import IconButton from '@mui/material/IconButton';
import Paper from '@mui/material/Paper';
import Stack from '@mui/material/Stack';
import Tooltip from '@mui/material/Tooltip';
import Typography from '@mui/material/Typography';
import RefreshIcon from '@mui/icons-material/Refresh';
import LaptopMacIcon from '@mui/icons-material/LaptopMac';
import { twinApi } from '../../twin/config/api';
import { ConnectedAgent } from '../../twin/types/connectedAgent';
import { formatShortDateTime } from '../../../shared/utils/dateUtils';

function formatAgentLabel(agent: ConnectedAgent): string {
  return agent.hostname || agent.device_id;
}

export default function ConnectedAgentsView() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [items, setItems] = useState<ConnectedAgent[]>([]);
  const [windowSec, setWindowSec] = useState(300);

  const connectedCount = useMemo(() => items.filter((x) => x.connected).length, [items]);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await twinApi.listConnectedAgents(300);
      setItems(result.items || []);
      setWindowSec(result.connected_within_sec || 300);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load connected agents');
      setItems([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  return (
    <Paper variant="outlined" sx={{ minHeight: 220 }}>
      <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ px: 2, py: 1.5 }}>
        <Stack direction="row" spacing={1} alignItems="center">
          <LaptopMacIcon fontSize="small" />
          <Typography variant="subtitle2">Connected TrustEdge agents</Typography>
          <Chip
            size="small"
            label={`${connectedCount}/${items.length}`}
            color={connectedCount > 0 ? 'success' : 'default'}
            variant="outlined"
          />
        </Stack>
        <Tooltip title="Refresh">
          <IconButton size="small" onClick={load} disabled={loading}>
            <RefreshIcon fontSize="small" />
          </IconButton>
        </Tooltip>
      </Stack>
      <Divider />

      <Box sx={{ p: 2 }}>
        <Typography variant="caption" color="text.secondary">
          Connected means seen in the last {windowSec} seconds.
        </Typography>
      </Box>

      <Box sx={{ px: 2, pb: 2 }}>
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 3 }}>
            <CircularProgress size={24} />
          </Box>
        ) : error ? (
          <Typography variant="body2" color="error">
            {error}
          </Typography>
        ) : items.length === 0 ? (
          <Typography variant="body2" color="text.secondary">
            No agent details received yet.
          </Typography>
        ) : (
          <Stack spacing={1}>
            {items.slice(0, 12).map((agent, idx) => (
              <Box
                key={`${agent.device_id}-${idx}`}
                component={RouterLink}
                to={`/agents/${encodeURIComponent(agent.device_id)}`}
                sx={{ textDecoration: 'none', color: 'inherit', display: 'block' }}
              >
                <Stack direction="row" alignItems="center" justifyContent="space-between" gap={1}>
                  <Stack spacing={0.25} sx={{ minWidth: 0 }}>
                    <Typography variant="body2" sx={{ fontWeight: 600 }} noWrap>
                      {formatAgentLabel(agent)}
                    </Typography>
                    <Typography variant="caption" color="text.secondary" noWrap>
                      {agent.os || 'OS unknown'}
                      {agent.os_version ? ` ${agent.os_version}` : ''}
                      {agent.agent_version ? ` · agent ${agent.agent_version}` : ''}
                      {agent.public_ip ? ` · ${agent.public_ip}` : ''}
                    </Typography>
                  </Stack>
                  <Stack direction="row" spacing={0.5} alignItems="center">
                    {agent.network_type && (
                      <Chip size="small" label={agent.network_type} variant="outlined" />
                    )}
                    <Chip
                      size="small"
                      label={agent.connected ? 'Connected' : 'Idle'}
                      color={agent.connected ? 'success' : 'default'}
                    />
                  </Stack>
                </Stack>
                <Typography variant="caption" color="text.secondary">
                  last seen: {agent.last_seen_at ? formatShortDateTime(agent.last_seen_at) : 'unknown'}
                  {typeof agent.established_count === 'number' ? ` · established ${agent.established_count}` : ''}
                  {typeof agent.listening_count === 'number' ? ` · listening ${agent.listening_count}` : ''}
                </Typography>
                {idx < items.length - 1 && <Divider sx={{ mt: 1 }} />}
              </Box>
            ))}
          </Stack>
        )}
      </Box>
    </Paper>
  );
}
