import { useEffect, useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import Box from '@mui/material/Box';
import CircularProgress from '@mui/material/CircularProgress';
import Link from '@mui/material/Link';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import DashboardCard from './DashboardCard';
import { twinApi } from '../../../twin/config/api';
import { ConnectedAgent } from '../../../twin/types/connectedAgent';

function formatAgentLabel(agent: ConnectedAgent): string {
  return agent.hostname || agent.device_id;
}

export default function TopAgentsCard() {
  const [loading, setLoading] = useState(true);
  const [items, setItems] = useState<ConnectedAgent[]>([]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const result = await twinApi.listConnectedAgents(300);
        if (!cancelled) setItems(result.items || []);
      } catch {
        if (!cancelled) setItems([]);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const ranked = [...items]
    .sort((a, b) => (b.established_count ?? 0) - (a.established_count ?? 0))
    .slice(0, 6);

  const maxConns = Math.max(1, ...ranked.map((a) => a.established_count ?? 0));

  return (
    <DashboardCard
      title="Top agents by connections"
      action={
        <Link component={RouterLink} to="/agents" variant="caption" underline="hover" color="text.secondary">
          Show all
        </Link>
      }
    >
      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
          <CircularProgress size={24} />
        </Box>
      ) : ranked.length === 0 ? (
        <Typography variant="body2" color="text.secondary" sx={{ py: 4, textAlign: 'center' }}>
          No agent activity yet.
        </Typography>
      ) : (
        <Stack spacing={1.5}>
          {ranked.map((agent) => {
            const conns = agent.established_count ?? 0;
            const pct = Math.round((conns / maxConns) * 100);
            return (
              <Box
                key={agent.device_id}
                component={RouterLink}
                to={`/agents/${encodeURIComponent(agent.device_id)}`}
                sx={{ textDecoration: 'none', color: 'inherit' }}
              >
                <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 0.5 }}>
                  <Typography variant="body2" sx={{ fontWeight: 500 }} noWrap>
                    {formatAgentLabel(agent)}
                  </Typography>
                  <Stack direction="row" spacing={1} alignItems="center">
                    <Typography
                      variant="caption"
                      sx={{
                        color: 'text.secondary',
                        bgcolor: 'action.hover',
                        px: 0.75,
                        py: 0.15,
                        borderRadius: '4px',
                        fontWeight: 500,
                      }}
                    >
                      {agent.os || 'Unknown'}
                    </Typography>
                    <Typography variant="body2" sx={{ fontWeight: 600, minWidth: 36, textAlign: 'right' }}>
                      {pct}%
                    </Typography>
                  </Stack>
                </Stack>
                <Box
                  sx={{
                    height: 4,
                    borderRadius: 2,
                    bgcolor: 'action.hover',
                    overflow: 'hidden',
                  }}
                >
                  <Box
                    sx={{
                      height: '100%',
                      width: `${pct}%`,
                      bgcolor: 'primary.main',
                      borderRadius: 2,
                    }}
                  />
                </Box>
              </Box>
            );
          })}
        </Stack>
      )}
    </DashboardCard>
  );
}
